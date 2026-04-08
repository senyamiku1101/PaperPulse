"""论文筛选模块 - 多级漏斗策略保留优质论文

筛选逻辑：
1. 著名期刊论文 → 全部保留
2. 指定课题组论文 → 全部保留
3. 其余论文 → 按引用量+时间分层筛选
4. 领域论文总数较少时 → 放宽/跳过筛选
"""

import json
import logging
from datetime import datetime

from scripts.config import (
    DATA_DIR,
    PRESTIGIOUS_JOURNAL_ISSNS,
    CITATION_THRESHOLDS,
    LOW_VOLUME_THRESHOLD,
    RESEARCH_GROUPS,
)

logger = logging.getLogger(__name__)

# 预处理：指定课题组的 author_id 集合
_GROUP_AUTHOR_IDS: set[str] = set()
for _g in RESEARCH_GROUPS:
    for _aid in _g.get("author_ids", []):
        _GROUP_AUTHOR_IDS.add(_aid)


def _is_prestigious_source(source_issn: list[str]) -> bool:
    """检查论文来源是否为著名期刊（基于 ISSN 匹配）"""
    if not source_issn:
        return False
    return bool(set(source_issn) & PRESTIGIOUS_JOURNAL_ISSNS)


def _is_group_paper(authors: list[dict]) -> bool:
    """检查论文是否来自指定课题组的成员"""
    for author in authors:
        author_id = author.get("id", "")
        if author_id and author_id in _GROUP_AUTHOR_IDS:
            return True
    return False


def _passes_citation_filter(paper: dict, current_year: int) -> bool:
    """按引用量+时间分层判断论文是否通过筛选

    规则：
    - 2年内：引用 >= 1
    - 2-5年：引用 >= 3
    - 5年以上：引用 >= 5 或 年均引用 >= 1
    """
    cfg = CITATION_THRESHOLDS
    year = paper.get("year")
    citations = paper.get("citation_count", 0) or 0

    if not year:
        # 无年份信息的论文，保守保留
        return True

    age = current_year - year

    if age <= 0:
        # 当年论文，直接保留
        return True
    elif age * 365 <= cfg["recent_days"]:
        return citations >= cfg["recent_min_citations"]
    elif age * 365 <= cfg["mid_days"]:
        return citations >= cfg["mid_min_citations"]
    else:
        if citations >= cfg["old_min_citations"]:
            return True
        cites_per_year = citations / max(age, 1)
        return cites_per_year >= cfg["old_min_cites_per_year"]


def _classify_paper(paper: dict, current_year: int) -> str:
    """对论文进行分类，返回保留原因

    Returns:
        "prestigious" - 著名期刊
        "group" - 指定课题组
        "citation_pass" - 通过引用量筛选
        "filtered_out" - 未通过筛选
    """
    # 1. 著名期刊 → 全部保留
    source_issn = paper.get("source", {}).get("issn", [])
    if _is_prestigious_source(source_issn):
        return "prestigious"

    # 2. 指定课题组 → 全部保留
    if _is_group_paper(paper.get("authors", [])):
        return "group"

    # 3. 引用量筛选
    if _passes_citation_filter(paper, current_year):
        return "citation_pass"

    return "filtered_out"


def filter_papers(papers: list[dict]) -> list[dict]:
    """对论文列表执行多级筛选

    Args:
        papers: 原始论文列表

    Returns:
        筛选后的论文列表（保留顺序不变）
    """
    current_year = datetime.now().year
    total = len(papers)

    # 如果论文总数较少，跳过筛选
    if total <= LOW_VOLUME_THRESHOLD:
        logger.info(f"论文总数 {total} <= {LOW_VOLUME_THRESHOLD}，跳过筛选，全部保留")
        return papers

    stats = {
        "prestigious": 0,
        "group": 0,
        "citation_pass": 0,
        "filtered_out": 0,
    }

    filtered = []
    for paper in papers:
        category = _classify_paper(paper, current_year)
        stats[category] += 1

        if category != "filtered_out":
            filtered.append(paper)

    logger.info(
        f"筛选完成: {total} → {len(filtered)} 篇 "
        f"(著名期刊={stats['prestigious']}, "
        f"课题组={stats['group']}, "
        f"引用通过={stats['citation_pass']}, "
        f"筛除={stats['filtered_out']})"
    )

    return filtered


def run_filter_pipeline() -> int:
    """执行完整的筛选流水线：读取 papers.json → 筛选 → 写回

    Returns:
        被筛除的论文数量
    """
    papers_file = DATA_DIR / "papers.json"
    if not papers_file.exists():
        logger.warning("papers.json 不存在，跳过筛选")
        return 0

    with open(papers_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    papers = data.get("papers", [])
    original_count = len(papers)

    if original_count == 0:
        logger.info("无论文数据，跳过筛选")
        return 0

    filtered = filter_papers(papers)
    removed = original_count - len(filtered)

    if removed > 0:
        data["papers"] = filtered
        data["total_count"] = len(filtered)
        with open(papers_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"已更新 papers.json，筛除 {removed} 篇论文")
    else:
        logger.info("无需筛除任何论文")

    return removed
