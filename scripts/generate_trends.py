"""趋势热力图数据生成模块"""

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone

from scripts.config import DATA_DIR, SUBTOPIC_KEYWORDS, get_year_ranges

logger = logging.getLogger(__name__)

PAPERS_FILE = DATA_DIR / "papers.json"
TRENDS_FILE = DATA_DIR / "trends.json"


def load_papers() -> list:
    if PAPERS_FILE.exists():
        with open(PAPERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("papers", [])
    return []


def classify_subtopic(paper: dict) -> list[str]:
    """根据关键词将论文分类到子主题"""
    text = (
        (paper.get("title", "") + " " +
         paper.get("abstract", "") + " " +
         " ".join(paper.get("topics", [])))
    ).lower()

    # 也检查 AI 分析的关键词
    analysis = paper.get("analysis") or {}
    if isinstance(analysis, dict):
        keywords = analysis.get("keywords", [])
        if isinstance(keywords, list):
            text += " " + " ".join(keywords).lower()

    matched = []
    for subtopic, kw_list in SUBTOPIC_KEYWORDS.items():
        for kw in kw_list:
            if kw.lower() in text:
                matched.append(subtopic)
                break
    return matched


def _paper_info(p: dict) -> dict:
    """提取论文简要信息供 AI 摘要使用"""
    return {
        "title": p.get("title", ""),
        "year": p.get("year"),
        "authors": ", ".join(
            a.get("name", "") for a in (p.get("authors") or [])[:3]
        ),
        "abstract": (p.get("abstract", "") or "")[:200],
        "citations": p.get("citation_count", 0),
    }


def generate_trend_data():
    """生成趋势热力图数据（按主题分别生成 AI 周期摘要）"""
    papers = load_papers()
    if not papers:
        logger.warning("没有论文数据，跳过趋势生成")
        return

    year_ranges = get_year_ranges()

    # 加载缓存：period -> subtopic -> summary
    cached: dict[str, dict[str, str]] = {}
    if TRENDS_FILE.exists():
        try:
            with open(TRENDS_FILE, "r", encoding="utf-8") as f:
                old_data = json.load(f)
            for interval in old_data.get("intervals", []):
                st_summaries = interval.get("subtopic_summaries", {})
                if st_summaries:
                    cached[interval["period"]] = st_summaries
                # 兼容旧的 period_summary 字段
                old_summary = interval.get("period_summary", "")
                if old_summary and not st_summaries:
                    cached[interval["period"]] = {"_overall": old_summary}
        except Exception:
            pass

    # 按年份区间分桶
    buckets: dict[str, list] = defaultdict(list)
    for paper in papers:
        year = paper.get("year")
        if not year:
            continue
        for yr in year_ranges:
            if yr["start_year"] <= year <= yr["end_year"]:
                buckets[yr["period"]].append(paper)
                break

    # 初始化 DeepSeek 客户端
    client = None
    try:
        from scripts.deepseek_client import DeepSeekClient
        client = DeepSeekClient()
    except ValueError:
        logger.warning("DeepSeek API Key 未配置，跳过周期摘要生成")

    intervals = []
    for yr in year_ranges:
        bucket_papers = buckets.get(yr["period"], [])
        period = yr["period"]

        # 高引论文 Top 5
        top_papers = sorted(
            bucket_papers,
            key=lambda p: p.get("citation_count", 0),
            reverse=True,
        )[:5]
        top_papers_summary = [
            {
                "id": p.get("id", ""),
                "title": p.get("title", ""),
                "citations": p.get("citation_count", 0),
                "year": p.get("year"),
            }
            for p in top_papers
        ]

        # 高产作者 Top 5
        author_counter = Counter()
        for p in bucket_papers:
            for a in p.get("authors", []):
                name = a.get("name", "")
                if name:
                    author_counter[name] += 1
        top_authors = [
            {"name": name, "paper_count": count}
            for name, count in author_counter.most_common(5)
        ]

        # 发表期刊 Top 5
        venue_counter = Counter()
        for p in bucket_papers:
            source = p.get("source", {})
            venue = source.get("name", "")
            if venue:
                venue_counter[venue] += 1
        top_venues = [
            {"name": name, "count": count}
            for name, count in venue_counter.most_common(5)
        ]

        # 子主题分布 + 按主题分组论文
        subtopic_counts = defaultdict(int)
        subtopic_papers: dict[str, list] = defaultdict(list)
        for p in bucket_papers:
            for st in classify_subtopic(p):
                subtopic_counts[st] += 1
                subtopic_papers[st].append(p)

        interval_data = {
            "period": period,
            "start_year": yr["start_year"],
            "end_year": yr["end_year"],
            "paper_count": len(bucket_papers),
            "top_papers": top_papers_summary,
            "top_authors": top_authors,
            "top_venues": top_venues,
            "subtopics": dict(subtopic_counts),
        }

        # 按主题生成 AI 摘要
        if bucket_papers and client:
            subtopic_summaries = {}
            old_cached = cached.get(period, {})

            for st, st_papers in subtopic_papers.items():
                if not st_papers:
                    continue

                # 使用缓存（仅当论文数没变时）
                cache_key = f"{st}:{len(st_papers)}"
                if cache_key in old_cached:
                    subtopic_summaries[st] = old_cached[cache_key]
                    continue

                # 按引用排序取 top 20
                top_st = sorted(
                    st_papers,
                    key=lambda p: p.get("citation_count", 0),
                    reverse=True,
                )[:20]
                papers_info = [_paper_info(p) for p in top_st]

                logger.info(f"  生成摘要: {period} / {st} ({len(st_papers)} 篇)")
                summary = client.summarize_period(period, papers_info, subtopic=st)
                if summary:
                    subtopic_summaries[st] = summary

            if subtopic_summaries:
                interval_data["subtopic_summaries"] = subtopic_summaries
                logger.info(f"周期 {period}: 已生成 {len(subtopic_summaries)} 个主题摘要")

        intervals.append(interval_data)

    # 汇总子主题列表
    all_subtopics = list(SUBTOPIC_KEYWORDS.keys())

    trend_data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "year_range": [1960, datetime.now().year],
        "all_subtopics": all_subtopics,
        "subtopic_keywords": {k: v for k, v in SUBTOPIC_KEYWORDS.items()},
        "intervals": intervals,
    }

    with open(TRENDS_FILE, "w", encoding="utf-8") as f:
        json.dump(trend_data, f, ensure_ascii=False, indent=2)
    logger.info(f"趋势数据已生成: {len(intervals)} 个时间段, {len(papers)} 篇论文")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_trend_data()
