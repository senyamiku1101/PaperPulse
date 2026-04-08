"""AI 论文分析模块 - 使用 DeepSeek 生成中文综述（5并发）"""

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from scripts.config import DATA_DIR, ANALYSIS_DELAY
from scripts.deepseek_client import DeepSeekClient

logger = logging.getLogger(__name__)

PAPERS_FILE = DATA_DIR / "papers.json"
ANALYSIS_WORKERS = 5  # 分析并发数
SAVE_INTERVAL = 10
ANALYSIS_YEAR_CUTOFF = 2020  # 只分析此年份及之后的论文
RELEVANCE_THRESHOLD = 2     # 相关性低于此值的论文不保留


def load_papers() -> list:
    """加载论文列表"""
    if PAPERS_FILE.exists():
        with open(PAPERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("papers", [])
    return []


def save_papers(papers: list):
    """保存论文列表"""
    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_count": len(papers),
        "papers": papers,
    }
    with open(PAPERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _analyze_single_paper(
    idx: int,
    total: int,
    paper: dict,
    client: DeepSeekClient,
    progress_counter: list,
    counter_lock: threading.Lock,
    papers_snapshot: list,
    save_lock: threading.Lock,
):
    """分析单篇论文（供线程池调用）"""
    title = paper.get("title", "")
    abstract = paper.get("abstract", "")

    if not abstract.strip():
        paper["analysis"] = {
            "summary": "无摘要",
            "methods": "",
            "innovations": "",
            "conclusions": "",
            "relevance_score": 0,
            "keywords": [],
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
        return True

    try:
        analysis = client.analyze_paper(title, abstract)
        analysis["analyzed_at"] = datetime.now(timezone.utc).isoformat()
        paper["analysis"] = analysis

        with counter_lock:
            progress_counter[0] += 1
            done = progress_counter[0]
            logger.info(f"分析 [{done}/{total}]: {title[:60]}...")

        # 定期保存
        if done % SAVE_INTERVAL == 0:
            with save_lock:
                save_papers(papers_snapshot)
                logger.info(f"已保存进度 ({done}/{total})")

        return True
    except Exception as e:
        logger.error(f"分析失败 '{title[:50]}': {e}")
        paper["analysis"] = {
            "summary": "",
            "methods": "",
            "innovations": "",
            "conclusions": "",
            "relevance_score": 0,
            "keywords": [],
            "error": True,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
        return False


def analyze_unanalyzed_papers():
    """对所有未分析的论文执行 DeepSeek AI 分析（5并发）"""
    papers = load_papers()
    if not papers:
        logger.warning("没有找到论文数据，请先运行 fetch_papers")
        return

    # 筛选未分析的论文（仅2020年及以后）
    unanalyzed = []
    skipped_old = 0
    for p in papers:
        if p.get("analysis") is not None:
            continue  # 已分析
        year = p.get("year")
        if year and year < ANALYSIS_YEAR_CUTOFF:
            # 2019及更早：标记为跳过，不做逐篇AI分析
            if p.get("analysis") is None:
                p["analysis"] = {
                    "summary": "",
                    "methods": "",
                    "innovations": "",
                    "conclusions": "",
                    "relevance_score": 0,
                    "keywords": [],
                    "skipped": True,
                    "reason": f"{year}年论文，仅统计不逐篇分析",
                }
                skipped_old += 1
            continue
        if not p.get("abstract", "").strip():
            continue
        unanalyzed.append(p)

    if skipped_old:
        logger.info(f"已跳过 {skipped_old} 篇 {ANALYSIS_YEAR_CUTOFF-1} 年及更早的论文（将在热力图中以5年为单位总结）")

    logger.info(f"总计 {len(papers)} 篇论文，{len(unanalyzed)} 篇待分析（5并发）")

    if not unanalyzed:
        logger.info("所有论文已分析完毕")
        return

    client = DeepSeekClient()
    counter_lock = threading.Lock()
    save_lock = threading.Lock()
    progress_counter = [0]  # 用列表包装以便在线程间共享

    analyzed_count = 0
    error_count = 0

    with ThreadPoolExecutor(max_workers=ANALYSIS_WORKERS) as executor:
        futures = {
            executor.submit(
                _analyze_single_paper,
                i, len(unanalyzed), paper, client,
                progress_counter, counter_lock, papers, save_lock,
            ): paper
            for i, paper in enumerate(unanalyzed)
        }

        for future in as_completed(futures):
            try:
                success = future.result()
                if success:
                    analyzed_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"分析任务异常: {e}")
                error_count += 1

    # 移除相关性低于阈值的论文（仅针对已分析的非跳过论文）
    before_count = len(papers)
    papers[:] = [
        p for p in papers
        if (p.get("analysis") or {}).get("skipped")  # 跳过的老论文保留
        or (p.get("analysis") is not None
            and (p.get("analysis") or {}).get("relevance_score", 0) >= RELEVANCE_THRESHOLD)
    ]
    removed = before_count - len(papers)
    if removed:
        logger.info(f"已移除 {removed} 篇相关性低于 {RELEVANCE_THRESHOLD} 的论文")

    # 最终保存
    save_papers(papers)
    logger.info(f"分析完成: {analyzed_count} 篇成功, {error_count} 篇失败, {removed} 篇因低相关性移除")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    analyze_unanalyzed_papers()
