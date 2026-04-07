"""课题组追踪模块"""

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone

from scripts.config import DATA_DIR, RESEARCH_GROUPS
from scripts.openalex_client import OpenAlexClient

logger = logging.getLogger(__name__)

PAPERS_FILE = DATA_DIR / "papers.json"
GROUPS_FILE = DATA_DIR / "groups.json"


def load_papers() -> list:
    if PAPERS_FILE.exists():
        with open(PAPERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("papers", [])
    return []


def build_paper_index(papers: list) -> dict:
    """以论文 ID 为键建立索引"""
    return {p["id"]: p for p in papers if p.get("id")}


def track_research_groups():
    """追踪课题组的研究产出"""
    papers = load_papers()
    paper_index = build_paper_index(papers)
    client = OpenAlexClient()

    # 从 papers.json 中提取机构到论文的映射
    institution_paper_map: dict[str, list] = defaultdict(list)
    for p in papers:
        for author in p.get("authors", []):
            inst = author.get("institution", "")
            if inst:
                institution_paper_map[inst.lower()].append(p["id"])

    groups_data = []

    for group_def in RESEARCH_GROUPS:
        logger.info(f"追踪课题组: {group_def['name']}")

        group_papers = []

        # 方法1: 从已有论文中按机构匹配
        inst_query = group_def.get("institution_query", "").lower()
        inst_name = group_def.get("institution", "").lower()

        matched_ids = set()
        for inst_key in [inst_query, inst_name]:
            for key, ids in institution_paper_map.items():
                if inst_key and inst_key in key:
                    matched_ids.update(ids)

        # 方法2: 如果定义了 author_ids，直接从 OpenAlex 获取
        author_ids = group_def.get("author_ids", [])
        if author_ids:
            for aid in author_ids:
                try:
                    works = client.get_author_works(aid)
                    for raw in works:
                        pid = raw.get("id", "").replace("https://openalex.org/", "")
                        if pid and pid in paper_index:
                            matched_ids.add(pid)
                except Exception as e:
                    logger.warning(f"获取作者 {aid} 论文失败: {e}")

        # 构建课题组论文列表
        for pid in matched_ids:
            if pid in paper_index:
                group_papers.append(paper_index[pid])

        if not group_papers:
            logger.info(f"  {group_def['name']}: 未找到相关论文")
            continue

        # 最近论文 (Top 10 by year)
        recent = sorted(
            group_papers,
            key=lambda p: (p.get("year") or 0, p.get("citation_count") or 0),
            reverse=True,
        )[:10]

        recent_summary = [
            {
                "id": p.get("id", ""),
                "title": p.get("title", ""),
                "year": p.get("year"),
                "citations": p.get("citation_count", 0),
                "relevance_score": (p.get("analysis") or {}).get("relevance_score", 0),
            }
            for p in recent
        ]

        # 年度统计
        yearly_counts: dict[str, int] = defaultdict(int)
        for p in group_papers:
            year = p.get("year")
            if year:
                yearly_counts[str(year)] += 1

        # Top 关键词
        keyword_counter = Counter()
        for p in group_papers:
            analysis = p.get("analysis") or {}
            if isinstance(analysis, dict):
                for kw in (analysis.get("keywords") or []):
                    keyword_counter[kw] += 1
            for t in (p.get("topics") or []):
                keyword_counter[t] += 1

        top_keywords = [kw for kw, _ in keyword_counter.most_common(10)]

        group_entry = {
            "id": group_def["id"],
            "name": group_def["name"],
            "institution": group_def["institution"],
            "institution_query": group_def.get("institution_query", ""),
            "description": group_def["description"],
            "author_ids": author_ids,
            "total_papers": len(group_papers),
            "recent_papers": recent_summary,
            "paper_ids": [p["id"] for p in group_papers],
            "yearly_counts": dict(sorted(yearly_counts.items())),
            "top_keywords": top_keywords,
        }

        groups_data.append(group_entry)
        logger.info(f"  {group_def['name']}: {len(group_papers)} 篇论文")

    # 保存结果
    groups_output = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_groups": len(groups_data),
        "groups": groups_data,
    }

    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(groups_output, f, ensure_ascii=False, indent=2)
    logger.info(f"课题组数据已保存: {len(groups_data)} 个课题组")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    track_research_groups()
