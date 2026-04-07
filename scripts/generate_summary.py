"""汇总统计生成模块"""

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone

from scripts.config import DATA_DIR

logger = logging.getLogger(__name__)

PAPERS_FILE = DATA_DIR / "papers.json"
TRENDS_FILE = DATA_DIR / "trends.json"
GROUPS_FILE = DATA_DIR / "groups.json"
SUMMARY_FILE = DATA_DIR / "summary.json"


def generate_summary():
    """生成总体统计数据"""
    # 加载数据
    papers = []
    if PAPERS_FILE.exists():
        with open(PAPERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            papers = data.get("papers", [])

    total_groups = 0
    if GROUPS_FILE.exists():
        with open(GROUPS_FILE, "r", encoding="utf-8") as f:
            groups_data = json.load(f)
            total_groups = groups_data.get("total_groups", 0)

    if not papers:
        logger.warning("没有论文数据，跳过汇总生成")
        return

    # 总论文数与已分析数
    total_papers = len(papers)
    analyzed_papers = sum(1 for p in papers if p.get("analysis") and not p.get("analysis", {}).get("error"))

    # 日期范围
    years = [p.get("year") for p in papers if p.get("year")]
    date_range = {
        "earliest": min(years) if years else None,
        "latest": max(years) if years else None,
    }

    # 平均引用数
    citations = [p.get("citation_count", 0) for p in papers]
    avg_citations = round(sum(citations) / len(citations), 1) if citations else 0

    # 最高引论文
    most_cited = max(papers, key=lambda p: p.get("citation_count", 0))
    most_cited_info = {
        "id": most_cited.get("id", ""),
        "title": most_cited.get("title", ""),
        "citations": most_cited.get("citation_count", 0),
        "year": most_cited.get("year"),
    }

    # Top 关键词
    keyword_counter = Counter()
    for p in papers:
        analysis = p.get("analysis") or {}
        if isinstance(analysis, dict):
            for kw in (analysis.get("keywords") or []):
                keyword_counter[kw] += 1
        for t in (p.get("topics") or []):
            keyword_counter[t] += 1

    top_keywords = [
        {"keyword": kw, "count": count}
        for kw, count in keyword_counter.most_common(20)
    ]

    # 论文最多年份
    year_counter = Counter(years)
    peak_year_data = year_counter.most_common(1)
    peak_year = {
        "year": peak_year_data[0][0] if peak_year_data else None,
        "count": peak_year_data[0][1] if peak_year_data else 0,
    }

    # 年度分布
    papers_by_year = {str(y): c for y, c in sorted(year_counter.items())}

    # 相关度分布
    relevance_dist = Counter()
    for p in papers:
        analysis = p.get("analysis") or {}
        if isinstance(analysis, dict) and "relevance_score" in analysis:
            score = analysis["relevance_score"]
            if score >= 8:
                relevance_dist["high"] += 1
            elif score >= 5:
                relevance_dist["medium"] += 1
            else:
                relevance_dist["low"] += 1

    summary = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_papers": total_papers,
        "analyzed_papers": analyzed_papers,
        "date_range": date_range,
        "avg_citations": avg_citations,
        "most_cited": most_cited_info,
        "top_keywords": top_keywords,
        "peak_year": peak_year,
        "total_groups": total_groups,
        "papers_by_year": papers_by_year,
        "relevance_distribution": dict(relevance_dist),
    }

    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    logger.info(
        f"汇总统计已生成: {total_papers} 篇论文, "
        f"{analyzed_papers} 篇已分析, "
        f"{total_groups} 个课题组"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_summary()
