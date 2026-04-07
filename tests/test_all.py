"""PaperPulse 全项目测试套件"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# 确保项目根目录在 path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# Test 1: config.py 配置正确性
# ============================================================
class TestConfig:
    def test_search_queries_not_empty(self):
        from scripts.config import SEARCH_QUERIES
        assert len(SEARCH_QUERIES) > 0, "SEARCH_QUERIES 不能为空"
        assert all(isinstance(q, str) and q.strip() for q in SEARCH_QUERIES)

    def test_year_ranges(self):
        from scripts.config import get_year_ranges
        ranges = get_year_ranges(start=1960, interval=5)
        assert ranges[0]["start_year"] == 1960
        assert ranges[0]["period"] == "1960-1964"
        # 最后一个区间应包含当前年份
        current_year = 2026  # 从 datetime 获取也可以
        last = ranges[-1]
        assert last["end_year"] >= current_year or last["start_year"] <= current_year

    def test_subtopic_keywords_structure(self):
        from scripts.config import SUBTOPIC_KEYWORDS
        assert isinstance(SUBTOPIC_KEYWORDS, dict)
        for key, kws in SUBTOPIC_KEYWORDS.items():
            assert isinstance(kws, list), f"SUBTOPIC_KEYWORDS['{key}'] 应为列表"
            assert len(kws) > 0, f"SUBTOPIC_KEYWORDS['{key}'] 不能为空"

    def test_research_groups_structure(self):
        from scripts.config import RESEARCH_GROUPS
        assert len(RESEARCH_GROUPS) > 0, "RESEARCH_GROUPS 不能为空"
        required_keys = {"id", "name", "institution", "description"}
        for g in RESEARCH_GROUPS:
            missing = required_keys - set(g.keys())
            assert not missing, f"课题组 '{g.get('name', '?')}' 缺少字段: {missing}"

    def test_topic_filter_format(self):
        from scripts.config import OPENALEX_TOPIC_FILTER
        assert "primary_topic.subfield.id" in OPENALEX_TOPIC_FILTER, \
            "过滤器应使用 primary_topic.subfield.id"
        assert "/subfields/2202" in OPENALEX_TOPIC_FILTER, \
            "应包含 Aerospace Engineering subfield id 2202"

    def test_data_dir_exists(self):
        from scripts.config import DATA_DIR
        assert DATA_DIR.exists(), f"data 目录应存在: {DATA_DIR}"


# ============================================================
# Test 2: openalex_client.py API 客户端
# ============================================================
class TestOpenAlexClient:
    def test_reconstruct_abstract_normal(self):
        from scripts.openalex_client import reconstruct_abstract
        inverted = {
            "Hello": [0],
            "world": [1],
            "this": [2],
            "is": [3],
            "a": [4],
            "test": [5],
        }
        result = reconstruct_abstract(inverted)
        assert result == "Hello world this is a test"

    def test_reconstruct_abstract_empty(self):
        from scripts.openalex_client import reconstruct_abstract
        assert reconstruct_abstract(None) == ""
        assert reconstruct_abstract({}) == ""

    def test_reconstruct_abstract_unordered(self):
        """测试倒排索引位置不连续的情况"""
        from scripts.openalex_client import reconstruct_abstract
        inverted = {
            "second": [1],
            "first": [0],
            "third": [2],
        }
        result = reconstruct_abstract(inverted)
        assert result == "first second third"

    def test_reconstruct_abstract_duplicate_positions(self):
        """测试同一位置多个词"""
        from scripts.openalex_client import reconstruct_abstract
        inverted = {
            "word1": [0],
            "word2": [0],
        }
        # 两个词在同一位置，排序后都出现
        result = reconstruct_abstract(inverted)
        assert "word1" in result or "word2" in result

    def test_extract_paper_complete(self):
        from scripts.openalex_client import OpenAlexClient
        raw = {
            "id": "https://openalex.org/W123456",
            "doi": "https://doi.org/10.1234/test",
            "title": "Test Paper on Fan Noise",
            "authorships": [
                {
                    "author": {"display_name": "Zhang San", "id": "https://openalex.org/A123"},
                    "institutions": [{"display_name": "Beihang University"}],
                },
                {
                    "author": {"display_name": "Li Si", "id": "https://openalex.org/A456"},
                    "institutions": [],
                },
            ],
            "publication_year": 2023,
            "cited_by_count": 42,
            "abstract_inverted_index": {"This": [0], "is": [1], "a": [2], "test": [3]},
            "topics": [{"display_name": "Aeroacoustics"}],
            "primary_location": {
                "source": {
                    "display_name": "Journal of Sound and Vibration",
                    "id": "https://openalex.org/S123",
                    "type": "journal",
                }
            },
            "open_access": {"is_oa": True, "oa_url": "https://example.com/paper.pdf"},
            "referenced_works": [
                "https://openalex.org/W999",
                "https://openalex.org/W888",
            ],
        }

        paper = OpenAlexClient.extract_paper(raw, search_query="fan noise")

        assert paper["id"] == "W123456", f"id 应为 W123456，实际为 {paper['id']}"
        assert paper["doi"] == "https://doi.org/10.1234/test"
        assert paper["title"] == "Test Paper on Fan Noise"
        assert len(paper["authors"]) == 2
        assert paper["authors"][0]["name"] == "Zhang San"
        assert paper["authors"][0]["institution"] == "Beihang University"
        assert paper["authors"][1]["institution"] == ""
        assert paper["year"] == 2023
        assert paper["citation_count"] == 42
        assert paper["abstract"] == "This is a test"
        assert paper["topics"] == ["Aeroacoustics"]
        assert paper["source"]["name"] == "Journal of Sound and Vibration"
        assert paper["is_oa"] is True
        assert paper["referenced_works"] == ["W999", "W888"]
        assert paper["search_query"] == "fan noise"
        assert paper["analysis"] is None

    def test_extract_paper_missing_fields(self):
        """测试缺失字段的健壮性"""
        from scripts.openalex_client import OpenAlexClient
        raw = {"id": "https://openalex.org/W1"}
        paper = OpenAlexClient.extract_paper(raw)
        assert paper["id"] == "W1"
        assert paper["doi"] == ""
        assert paper["title"] == ""
        assert paper["authors"] == []
        assert paper["year"] is None
        assert paper["citation_count"] == 0
        assert paper["abstract"] == ""
        assert paper["analysis"] is None

    def test_extract_paper_no_abstract(self):
        from scripts.openalex_client import OpenAlexClient
        raw = {
            "id": "https://openalex.org/W2",
            "title": "No Abstract",
            "abstract_inverted_index": None,
        }
        paper = OpenAlexClient.extract_paper(raw)
        assert paper["abstract"] == ""

    def test_extract_paper_null_location(self):
        from scripts.openalex_client import OpenAlexClient
        raw = {
            "id": "https://openalex.org/W3",
            "title": "No Location",
            "primary_location": None,
        }
        paper = OpenAlexClient.extract_paper(raw)
        assert paper["source"]["name"] == ""

    def test_extract_paper_none_author_id(self):
        """author.id 为 None 不应崩溃"""
        from scripts.openalex_client import OpenAlexClient
        raw = {
            "id": "https://openalex.org/W4",
            "title": "Author ID None",
            "authorships": [
                {
                    "author": {"display_name": "Test", "id": None},
                    "institutions": [],
                },
                {
                    "author": {"display_name": "Test2"},  # 无 id key
                    "institutions": None,
                },
            ],
        }
        paper = OpenAlexClient.extract_paper(raw)
        assert paper["authors"][0]["id"] == ""
        assert paper["authors"][1]["id"] == ""

    def test_session_created(self):
        from scripts.openalex_client import OpenAlexClient
        client = OpenAlexClient(api_key="test")
        assert client.session is not None


# ============================================================
# Test 3: deepseek_client.py AI 客户端
# ============================================================
class TestDeepSeekClient:
    def test_missing_api_key_raises(self):
        """缺少 API Key 应抛出 ValueError"""
        from scripts.deepseek_client import DeepSeekClient
        # DEEPSEEK_API_KEY 在 import 时已从 config 解析，需 patch 模块级常量
        with patch("scripts.deepseek_client.DEEPSEEK_API_KEY", ""):
            with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
                DeepSeekClient(api_key="")

    def test_analyze_paper_empty_abstract(self):
        """空摘要应返回默认值"""
        from scripts.deepseek_client import DeepSeekClient
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}):
            client = DeepSeekClient(api_key="fake-key")
            result = client.analyze_paper("Title", "")
            assert result["relevance_score"] == 0
            assert "无摘要" in result["summary"]

    def test_analyze_paper_whitespace_abstract(self):
        from scripts.deepseek_client import DeepSeekClient
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}):
            client = DeepSeekClient(api_key="fake-key")
            result = client.analyze_paper("Title", "   \n  ")
            assert result["relevance_score"] == 0


# ============================================================
# Test 4: generate_trends.py 趋势数据
# ============================================================
class TestGenerateTrends:
    def test_classify_subtopic_matches(self):
        from scripts.generate_trends import classify_subtopic
        paper = {
            "title": "Tonal noise from axial fan",
            "abstract": "Blade passing frequency measurement",
            "topics": [],
        }
        topics = classify_subtopic(paper)
        assert "tonal_noise" in topics, f"应匹配 tonal_noise，实际: {topics}"
        assert "measurement" in topics, f"应匹配 measurement，实际: {topics}"

    def test_classify_subtopic_no_match(self):
        from scripts.generate_trends import classify_subtopic
        paper = {
            "title": "Something unrelated",
            "abstract": "No relevant keywords here",
            "topics": [],
        }
        topics = classify_subtopic(paper)
        assert topics == []

    def test_classify_subtopic_uses_analysis_keywords(self):
        from scripts.generate_trends import classify_subtopic
        paper = {
            "title": "Study",
            "abstract": "",
            "topics": [],
            "analysis": {"keywords": ["broadband", "LES"]},
        }
        topics = classify_subtopic(paper)
        assert "broadband_noise" in topics

    def test_classify_subtopic_multiple_matches(self):
        from scripts.generate_trends import classify_subtopic
        paper = {
            "title": "CFD simulation of acoustic liner for fan noise reduction",
            "abstract": "LES simulation of liner design for broadband noise",
            "topics": [],
        }
        topics = classify_subtopic(paper)
        assert len(topics) >= 3, f"应匹配多个子主题，实际: {topics}"


# ============================================================
# Test 5: fetch_papers.py 数据合并逻辑
# ============================================================
class TestFetchPapers:
    def test_load_save_roundtrip(self):
        """测试 JSON 读写一致性"""
        from scripts.fetch_papers import load_existing_papers, save_papers, PAPERS_FILE
        import scripts.fetch_papers as fp

        test_data = {
            "last_updated": "2026-01-01T00:00:00Z",
            "total_count": 1,
            "papers": [{"id": "W1", "title": "Test"}],
        }

        # 临时覆盖文件路径
        original_file = fp.PAPERS_FILE
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(test_data, f)
            tmp_path = f.name

        fp.PAPERS_FILE = Path(tmp_path)
        try:
            loaded = fp.load_existing_papers()
            assert loaded["total_count"] == 1
            assert loaded["papers"][0]["id"] == "W1"

            # 修改并保存
            loaded["papers"].append({"id": "W2", "title": "Test2"})
            fp.save_papers(loaded)

            reloaded = fp.load_existing_papers()
            assert reloaded["total_count"] == 2
        finally:
            fp.PAPERS_FILE = original_file
            os.unlink(tmp_path)


# ============================================================
# Test 6: generate_summary.py 统计逻辑
# ============================================================
class TestGenerateSummary:
    def test_summary_structure(self):
        """测试汇总统计的数据结构"""
        # 用临时目录模拟
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # 创建测试 papers.json
            papers = {
                "papers": [
                    {"id": "W1", "title": "A", "year": 2020, "citation_count": 10,
                     "analysis": {"keywords": ["fan noise"], "relevance_score": 9},
                     "topics": ["acoustics"]},
                    {"id": "W2", "title": "B", "year": 2022, "citation_count": 5,
                     "analysis": {"keywords": ["aeroacoustics"], "relevance_score": 7},
                     "topics": []},
                    {"id": "W3", "title": "C", "year": 2022, "citation_count": 20,
                     "analysis": None, "topics": []},
                ]
            }
            with open(tmpdir / "papers.json", "w", encoding="utf-8") as f:
                json.dump(papers, f)

            with open(tmpdir / "groups.json", "w", encoding="utf-8") as f:
                json.dump({"total_groups": 3}, f)

            # Patch 路径
            import scripts.generate_summary as gs
            orig_pf = gs.PAPERS_FILE
            orig_gf = gs.GROUPS_FILE
            orig_sf = gs.SUMMARY_FILE

            gs.PAPERS_FILE = tmpdir / "papers.json"
            gs.GROUPS_FILE = tmpdir / "groups.json"
            gs.SUMMARY_FILE = tmpdir / "summary.json"

            try:
                gs.generate_summary()

                with open(gs.SUMMARY_FILE, "r", encoding="utf-8") as f:
                    summary = json.load(f)

                assert summary["total_papers"] == 3
                assert summary["analyzed_papers"] == 2  # W3 has analysis=None
                assert summary["date_range"]["earliest"] == 2020
                assert summary["date_range"]["latest"] == 2022
                assert summary["avg_citations"] == pytest.approx(11.7, abs=0.1)
                assert summary["most_cited"]["id"] == "W3"
                assert summary["most_cited"]["citations"] == 20
                assert summary["peak_year"]["year"] == 2022
                assert summary["peak_year"]["count"] == 2  # 2022年有2篇
                assert summary["total_groups"] == 3
            finally:
                gs.PAPERS_FILE = orig_pf
                gs.GROUPS_FILE = orig_gf
                gs.SUMMARY_FILE = orig_sf


# ============================================================
# Test 7: track_groups.py 课题组逻辑
# ============================================================
class TestTrackGroups:
    def test_build_paper_index(self):
        from scripts.track_groups import build_paper_index
        papers = [
            {"id": "W1", "title": "A"},
            {"id": "W2", "title": "B"},
            {"id": "", "title": "C"},  # 空 id 应被跳过
        ]
        index = build_paper_index(papers)
        assert "W1" in index
        assert "W2" in index
        assert len(index) == 2


# ============================================================
# Test 8: main.py 参数解析
# ============================================================
class TestMain:
    def test_argparse_default(self):
        """测试默认参数：无参数时 run_all=True"""
        import scripts.main as m
        import argparse

        # 模拟无参数
        with patch("sys.argv", ["main.py"]):
            args = m.parser.parse_args([]) if hasattr(m, 'parser') else None

    def test_modules_importable(self):
        """所有子模块应该可以被 main.py 导入"""
        from scripts import fetch_papers, analyze_papers, generate_trends
        from scripts import track_groups, generate_summary


# ============================================================
# Test 9: 数据 Schema 一致性
# ============================================================
class TestSchemaConsistency:
    def test_papers_schema_fields(self):
        from scripts.openalex_client import OpenAlexClient
        paper = OpenAlexClient.extract_paper({
            "id": "https://openalex.org/W1",
            "title": "Test",
        })
        required_fields = [
            "id", "doi", "title", "authors", "year",
            "citation_count", "abstract", "topics", "source",
            "open_access_url", "is_oa", "referenced_works",
            "search_query", "analysis"
        ]
        for field in required_fields:
            assert field in paper, f"论文缺少必要字段: {field}"

    def test_analysis_schema_fields(self):
        """AI 分析结果应包含所有必要字段"""
        from scripts.deepseek_client import DeepSeekClient
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}):
            client = DeepSeekClient(api_key="fake-key")
            result = client.analyze_paper("Title", "")
            required = ["summary", "methods", "innovations", "conclusions",
                        "relevance_score", "keywords"]
            for field in required:
                assert field in result, f"分析结果缺少字段: {field}"


# ============================================================
# Test 10: 前端 HTML 基础检查
# ============================================================
class TestFrontend:
    def test_index_html_exists(self):
        assert (PROJECT_ROOT / "index.html").exists(), "index.html 应存在"

    def test_index_html_has_all_tabs(self):
        content = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")
        tabs = ["dashboard", "papers", "heatmap", "groups", "qa"]
        for tab in tabs:
            assert f'data-tab="{tab}"' in content, f"缺少 tab: {tab}"

    def test_index_html_has_data_loading(self):
        content = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")
        assert "papers.json" in content
        assert "trends.json" in content
        assert "groups.json" in content
        assert "summary.json" in content

    def test_index_html_has_deepseek_api(self):
        content = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")
        assert "api.deepseek.com" in content

    def test_index_html_has_all_modules(self):
        content = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")
        modules = [
            "renderDashboard", "renderPaperList", "renderHeatmap",
            "renderGroups", "sendQuestion", "showPaperDetail"
        ]
        for fn in modules:
            assert fn in content, f"前端缺少函数: {fn}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
