"""课题组自动发现模块 - 基于机构归一化 + 共著网络聚类

流程：
1. 从 papers.json 提取所有作者及其机构
2. 归一化机构名称（去停用词 + 相似度匹配）
3. 按机构内构建共著关系图
4. 连通分量 = 课题组
5. 输出 groups.json（兼容现有 schema）
"""

import json
import logging
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher

from scripts.config import DATA_DIR

logger = logging.getLogger(__name__)

PAPERS_FILE = DATA_DIR / "papers.json"
GROUPS_FILE = DATA_DIR / "groups.json"

# 机构名归一化停用词
INST_STOPWORDS = {
    "university", "institute", "dept", "department",
    "lab", "laboratory", "center", "centre",
    "college", "of", "the", "school", "faculty",
    "division", "section", "group", "chair",
}

# 机构名已知别名映射（手动补充，解决缩写问题）
INST_ALIASES = {
    "mit": "massachusetts institute technology",
    "m.i.t": "massachusetts institute technology",
    "caltech": "california institute technology",
    "gt": "georgia tech",
    "gatech": "georgia tech",
    "georgia institute technology": "georgia tech",
    "nasa glenn": "nasa glenn research center",
    "nasa langley": "nasa langley research center",
    "dlr": "deutsches zentrum luft raumfahrt",
    "onera": "office national etudes recherches aerospatiales",
    "buaa": "beihang",
    "sjtu": "shanghai jiao tong",
    "isvr": "institute sound vibration research southampton",
    "cambridge": "cambridge",
    "whittle": "cambridge whittle",
}

# 相似度阈值
SIMILARITY_THRESHOLD = 0.85

# 课题组最低要求
MIN_AUTHORS_PER_GROUP = 2
MIN_PAPERS_PER_GROUP = 2


def _norm_inst(name: str) -> str:
    """归一化机构名：小写、去标点、去停用词"""
    if not name:
        return ""
    s = name.lower().strip()
    # 去标点
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    # 去停用词
    tokens = [t for t in s.split() if t and t not in INST_STOPWORDS]
    result = " ".join(tokens)

    # 检查别名
    for alias, canonical in INST_ALIASES.items():
        if alias in result or result in alias:
            return canonical

    return result


def _find_canonical(norm: str, canonical_list: list[str]) -> str:
    """在已有标准名列表中找到最匹配的，或创建新的"""
    if not norm:
        return "unknown"

    best = None
    best_score = 0.0
    for c in canonical_list:
        score = SequenceMatcher(None, norm, c).ratio()
        if score > best_score:
            best_score = score
            best = c

    if best_score >= SIMILARITY_THRESHOLD:
        return best

    canonical_list.append(norm)
    return norm


def _connected_components(adj: dict[str, set[str]]) -> list[list[str]]:
    """DFS 求连通分量"""
    seen: set[str] = set()
    components = []
    for node in adj:
        if node in seen:
            continue
        stack = [node]
        seen.add(node)
        comp = []
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj.get(u, set()):
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        components.append(comp)
    return components


def _slug(name: str) -> str:
    """生成 URL-safe 的简短标识"""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")[:30]


def discover_groups():
    """自动发现课题组并生成 groups.json"""
    if not PAPERS_FILE.exists():
        logger.warning("papers.json 不存在，跳过课题组发现")
        return

    with open(PAPERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    papers = data.get("papers", [])

    if not papers:
        logger.warning("无论文数据")
        return

    # ====== Step 1: 机构归一化 ======
    canonical_names: list[str] = []  # 已知标准名列表
    # raw_name -> canonical_norm -> display_name 的映射
    inst_display: dict[str, str] = {}  # norm -> 最长的原始名（用于显示）

    # author_id -> primary institution norm
    author_inst: dict[str, str] = {}

    # 为每个作者统计机构出现频率，确定主要机构
    author_inst_counter: dict[str, Counter] = defaultdict(Counter)

    for paper in papers:
        for author in paper.get("authors", []):
            aid = author.get("id", "")
            inst_raw = author.get("institution", "")
            if not aid or not inst_raw:
                continue
            norm = _norm_inst(inst_raw)
            canonical = _find_canonical(norm, canonical_names)
            author_inst_counter[aid][canonical] += 1

            # 记录显示名（取最长的作为标准显示名）
            if canonical not in inst_display or len(inst_raw) > len(inst_display.get(canonical, "")):
                inst_display[canonical] = inst_raw

    # 确定每个作者的主要机构
    for aid, counter in author_inst_counter.items():
        author_inst[aid] = counter.most_common(1)[0][0]

    logger.info(f"归一化完成: 发现 {len(canonical_names)} 个机构, {len(author_inst)} 位作者")

    # ====== Step 2: 按机构分组论文 ======
    # inst_norm -> list of (paper_id, [author_ids in this inst])
    inst_papers: dict[str, list[tuple[str, list[str]]]] = defaultdict(list)

    for paper in papers:
        pid = paper.get("id", "")
        if not pid:
            continue
        # 找出属于每个机构的作者
        paper_authors_by_inst: dict[str, list[str]] = defaultdict(list)
        for author in paper.get("authors", []):
            aid = author.get("id", "")
            if not aid:
                continue
            inst = author_inst.get(aid, "")
            if inst:
                paper_authors_by_inst[inst].append(aid)

        for inst, aids in paper_authors_by_inst.items():
            if aids:
                inst_papers[inst].append((pid, aids))

    # ====== Step 3: 机构内共著网络 → 连通分量 ======
    paper_index = {p["id"]: p for p in papers if p.get("id")}
    groups_data = []

    for inst_norm, paper_list in inst_papers.items():
        if inst_norm == "unknown":
            continue

        # 构建邻接表
        adj: dict[str, set[str]] = defaultdict(set)
        for pid, aids in paper_list:
            for a in aids:
                adj[a].add(a)  # 确保孤立节点也在图中
            for i in range(len(aids)):
                for j in range(i + 1, len(aids)):
                    adj[aids[i]].add(aids[j])
                    adj[aids[j]].add(aids[i])

        # 求连通分量
        components = _connected_components(dict(adj))

        display_name = inst_display.get(inst_norm, inst_norm.title())
        inst_slug = _slug(inst_norm)

        for idx, comp_authors in enumerate(components, 1):
            if len(comp_authors) < MIN_AUTHORS_PER_GROUP:
                continue

            # 收集该分量（课题组）的论文
            comp_set = set(comp_authors)
            group_paper_ids = []
            for pid, aids in paper_list:
                if comp_set & set(aids):  # 至少一个作者在该分量中
                    group_paper_ids.append(pid)

            if len(group_paper_ids) < MIN_PAPERS_PER_GROUP:
                continue

            # 找核心作者（论文数最多的）
            author_paper_count = Counter()
            for pid in group_paper_ids:
                p = paper_index.get(pid, {})
                for a in p.get("authors", []):
                    aid = a.get("id", "")
                    if aid in comp_set:
                        author_paper_count[a.get("name", "")] += 1

            top_author_name = author_paper_count.most_common(1)[0][0] if author_paper_count else ""

            # 命名
            if len(components) == 1:
                group_name = display_name
            else:
                group_name = f"{display_name} – {top_author_name.split()[-1] if top_author_name else idx}"

            group_id = f"group_{inst_slug}_{idx}"

            # 最近论文 (Top 10)
            group_papers = [paper_index[pid] for pid in group_paper_ids if pid in paper_index]
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

            groups_data.append({
                "id": group_id,
                "name": group_name,
                "institution": display_name,
                "institution_query": display_name,
                "description": f"自动发现：{len(comp_authors)} 位作者，{len(group_paper_ids)} 篇论文",
                "author_ids": comp_authors,
                "total_papers": len(group_paper_ids),
                "recent_papers": recent_summary,
                "paper_ids": group_paper_ids,
                "yearly_counts": dict(sorted(yearly_counts.items())),
                "top_keywords": [kw for kw, _ in keyword_counter.most_common(10)],
                "auto_discovered": True,
            })

    # 按论文数降序排列
    groups_data.sort(key=lambda g: g["total_papers"], reverse=True)

    # 保存
    output = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_groups": len(groups_data),
        "groups": groups_data,
    }
    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"课题组自动发现完成: {len(groups_data)} 个课题组")
    for g in groups_data[:10]:
        logger.info(f"  {g['name']}: {g['total_papers']} 篇, {len(g['author_ids'])} 位作者")
    if len(groups_data) > 10:
        logger.info(f"  ... 还有 {len(groups_data)-10} 个课题组")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    discover_groups()
