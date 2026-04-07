"""论文抓取模块 - 从 OpenAlex 批量抓取风扇噪声相关论文（8并发）"""

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from scripts.config import DATA_DIR, SEARCH_QUERIES, MAX_PAPERS_PER_QUERY, OPENALEX_TOPIC_FILTER
from scripts.openalex_client import OpenAlexClient

logger = logging.getLogger(__name__)

PAPERS_FILE = DATA_DIR / "papers.json"
FETCH_WORKERS = 8  # 抓取并发数


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


def _fetch_single_query(
    query: str,
    paper_index: dict,
    index_lock: threading.Lock,
):
    """抓取单个搜索词的所有论文（供线程池调用）"""
    client = OpenAlexClient()
    count = 0
    cursor = None
    local_new = 0

    while count < MAX_PAPERS_PER_QUERY:
        try:
            results, next_cursor = client.search_works(
                query=query,
                filters=OPENALEX_TOPIC_FILTER or None,
                per_page=100,
                cursor=cursor,
            )
        except Exception as e:
            logger.error(f"搜索 '{query}' 失败: {e}")
            break

        if not results:
            break

        with index_lock:
            for raw in results:
                paper = OpenAlexClient.extract_paper(raw, search_query=query)
                pid = paper["id"]
                if pid and pid not in paper_index:
                    paper_index[pid] = paper
                    local_new += 1
                elif pid and pid in paper_index:
                    paper_index[pid]["citation_count"] = paper["citation_count"]
                    paper_index[pid]["search_query"] = paper["search_query"]

        count += len(results)
        logger.info(f"  '{query}': 已获取 {count} 篇 (新 {local_new})")

        if not next_cursor:
            break
        cursor = next_cursor

    return query, count, local_new


def fetch_all_papers():
    """从 OpenAlex 抓取所有搜索词相关的论文（8并发）"""
    existing = load_existing_papers()

    # 以 openalex_id 为键建立索引，保留已有分析
    paper_index = {}
    for p in existing["papers"]:
        paper_index[p["id"]] = p

    logger.info(f"已有 {len(paper_index)} 篇论文，开始 8 并发增量抓取...")

    index_lock = threading.Lock()
    total_new = 0

    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as executor:
        futures = {
            executor.submit(_fetch_single_query, query, paper_index, index_lock): query
            for query in SEARCH_QUERIES
        }

        for future in as_completed(futures):
            query = futures[future]
            try:
                _, count, new = future.result()
                total_new += new
                logger.info(f"完成 '{query}': {count} 篇, 新增 {new} 篇")
            except Exception as e:
                logger.error(f"搜索 '{query}' 异常: {e}")

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
    logger.info(f"抓取完成，新增 {total_new} 篇，总计 {len(papers)} 篇")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch_all_papers()