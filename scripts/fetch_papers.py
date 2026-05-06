"""论文抓取模块 - 从种子 DOI 构建引用图谱（4并发）"""

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from scripts.config import DATA_DIR, SEED_DOIS_FILE, CITATION_CONFIG
from scripts.openalex_client import OpenAlexClient

logger = logging.getLogger(__name__)

PAPERS_FILE = DATA_DIR / "papers.json"
FETCH_WORKERS = 4


def load_existing_papers() -> dict:
    """加载已有的 papers.json"""
    if PAPERS_FILE.exists():
        with open(PAPERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_updated": "", "total_count": 0, "papers": []}


def save_papers(data: dict):
    """保存 papers.json"""
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    data["total_count"] = len(data["papers"])
    with open(PAPERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存 {data['total_count']} 篇论文到 {PAPERS_FILE}")


def load_seed_dois() -> list[dict]:
    """加载种子 DOI 列表"""
    if not SEED_DOIS_FILE.exists():
        logger.warning(f"种子 DOI 文件不存在: {SEED_DOIS_FILE}")
        return []
    with open(SEED_DOIS_FILE, "r", encoding="utf-8") as f:
        seeds = json.load(f)
    if not seeds:
        logger.warning("种子 DOI 文件为空")
    return seeds


def _fetch_seed_citation_graph(
    seed_entry: dict,
    paper_index: dict,
    index_lock: threading.Lock,
):
    """抓取单个种子论文的引用图谱（供线程池调用）"""
    doi = seed_entry["doi"]
    label = seed_entry.get("label", doi)
    client = OpenAlexClient()
    local_new = 0

    logger.info(f"处理种子 DOI: {label}")

    # 1. 获取种子论文本身
    raw_seed = client.get_work_by_doi(doi)
    if not raw_seed:
        logger.error(f"无法获取种子论文: {doi}")
        return doi, 0

    seed_paper = OpenAlexClient.extract_paper(raw_seed, discovery_origin="seed", seed_doi=doi)
    seed_id = seed_paper["id"]
    clean_seed_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")

    with index_lock:
        if seed_id and seed_id not in paper_index:
            paper_index[seed_id] = seed_paper
            local_new += 1
        elif seed_id:
            paper_index[seed_id]["citation_count"] = seed_paper["citation_count"]
            paper_index[seed_id]["referenced_works"] = seed_paper["referenced_works"]
            paper_index[seed_id]["discovery_origin"] = "seed"
            paper_index[seed_id]["seed_doi"] = clean_seed_doi

    # 2. 获取参考文献（种子论文引用的论文）
    referenced_ids = seed_paper.get("referenced_works", [])
    max_refs = CITATION_CONFIG["max_references_per_seed"]
    if len(referenced_ids) > max_refs:
        logger.info(f"  参考文献数 {len(referenced_ids)} 超限，截取前 {max_refs} 篇")
        referenced_ids = referenced_ids[:max_refs]

    if referenced_ids:
        logger.info(f"  获取 {len(referenced_ids)} 篇参考文献...")
        ref_results = client.get_works_by_ids(
            referenced_ids,
            batch_size=CITATION_CONFIG["batch_size"],
        )
        ref_count = 0
        with index_lock:
            for raw in ref_results:
                paper = OpenAlexClient.extract_paper(raw, discovery_origin="reference", seed_doi=clean_seed_doi)
                pid = paper["id"]
                if pid and pid not in paper_index:
                    paper_index[pid] = paper
                    local_new += 1
                    ref_count += 1
                elif pid:
                    paper_index[pid]["citation_count"] = paper["citation_count"]
                    paper_index[pid]["referenced_works"] = paper["referenced_works"]
        logger.info(f"  参考文献: 获取 {len(ref_results)} 篇, 新增 {ref_count} 篇")

    # 3. 获取引用文献（引用了种子论文的论文）
    if seed_id:
        logger.info(f"  获取引用种子论文的文献...")
        citing_results = client.get_citing_works(
            seed_id,
            max_results=CITATION_CONFIG["max_citers_per_seed"],
        )
        citing_count = 0
        with index_lock:
            for raw in citing_results:
                paper = OpenAlexClient.extract_paper(raw, discovery_origin="citing", seed_doi=clean_seed_doi)
                pid = paper["id"]
                if pid and pid not in paper_index:
                    paper_index[pid] = paper
                    local_new += 1
                    citing_count += 1
                elif pid:
                    paper_index[pid]["citation_count"] = paper["citation_count"]
                    paper_index[pid]["referenced_works"] = paper["referenced_works"]
        logger.info(f"  引用文献: 获取 {len(citing_results)} 篇, 新增 {citing_count} 篇")

    return doi, local_new


def fetch_citation_graph():
    """从种子 DOI 构建引用图谱"""
    existing = load_existing_papers()

    # 以 openalex_id 为键建立索引，保留已有分析
    paper_index = {}
    for p in existing["papers"]:
        paper_index[p["id"]] = p

    seeds = load_seed_dois()
    if not seeds:
        logger.warning("没有种子 DOI，跳过抓取")
        return

    logger.info(f"已有 {len(paper_index)} 篇论文，开始处理 {len(seeds)} 个种子 DOI（{FETCH_WORKERS} 并发）...")

    index_lock = threading.Lock()
    total_new = 0

    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as executor:
        futures = {
            executor.submit(_fetch_seed_citation_graph, seed, paper_index, index_lock): seed["doi"]
            for seed in seeds
        }

        for future in as_completed(futures):
            doi = futures[future]
            try:
                _, new = future.result()
                total_new += new
                logger.info(f"完成种子 {doi}: 新增 {new} 篇")
            except Exception as e:
                logger.error(f"种子 {doi} 处理异常: {e}")

    # 排序：年份降序 → 引用数降序
    papers = sorted(
        paper_index.values(),
        key=lambda p: (p.get("year") or 0, p.get("citation_count") or 0),
        reverse=True,
    )

    save_papers({
        "last_updated": "",
        "total_count": len(papers),
        "papers": papers,
    })
    logger.info(f"引用图谱构建完成，新增 {total_new} 篇，总计 {len(papers)} 篇")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch_citation_graph()
