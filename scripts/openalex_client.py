"""OpenAlex API 封装模块"""

import logging
import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scripts.config import (
    OPENALEX_BASE_URL,
    OPENALEX_API_KEY,
    OPENALEX_EMAIL,
    REQUEST_DELAY,
)

logger = logging.getLogger(__name__)


class OpenAlexClient:
    """OpenAlex API 客户端，支持 cursor 分页和自动重试"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        email: Optional[str] = None,
    ):
        self.api_key = api_key or OPENALEX_API_KEY
        self.email = email or OPENALEX_EMAIL
        self.session = self._create_session()
        self._last_request_time = 0.0

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503],
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _wait_rate_limit(self):
        """确保请求间隔不低于 REQUEST_DELAY"""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """发送 GET 请求到 OpenAlex API"""
        params = params or {}
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["mailto"] = self.email

        self._wait_rate_limit()

        url = f"{OPENALEX_BASE_URL}{endpoint}"
        logger.debug(f"GET {url} params={params}")

        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def search_works(
        self,
        query: str,
        filters: Optional[str] = None,
        per_page: int = 100,
        cursor: Optional[str] = None,
    ) -> tuple[list[dict], Optional[str]]:
        """搜索论文，返回 (结果列表, next_cursor)"""
        params = {
            "search": query,
            "per_page": min(per_page, 200),
            "select": "id,doi,title,authorships,publication_year,cited_by_count,"
                      "abstract_inverted_index,topics,primary_location,open_access,"
                      "referenced_works,keywords",
        }
        if filters:
            params["filter"] = filters
        if cursor:
            params["cursor"] = cursor

        data = self._get("/works", params)
        results = data.get("results", [])
        next_cursor = data.get("meta", {}).get("next_cursor")
        return results, next_cursor

    def get_work(self, openalex_id: str) -> dict:
        """获取单篇论文详情"""
        return self._get(f"/works/{openalex_id}")

    def search_authors(self, query: str, per_page: int = 20) -> list[dict]:
        """搜索作者"""
        params = {"search": query, "per_page": per_page}
        data = self._get("/authors", params)
        return data.get("results", [])

    def get_author_works(self, author_id: str, per_page: int = 100) -> list[dict]:
        """获取作者的所有论文"""
        all_works = []
        cursor = None
        while True:
            params: dict = {
                "filter": f"author.id:{author_id}",
                "per_page": min(per_page, 200),
                "select": "id,doi,title,publication_year,cited_by_count,"
                          "abstract_inverted_index,topics,primary_location,open_access",
            }
            if cursor:
                params["cursor"] = cursor
            data = self._get("/works", params)
            results = data.get("results", [])
            all_works.extend(results)
            cursor = data.get("meta", {}).get("next_cursor")
            if not cursor or not results:
                break
        return all_works

    def search_institutions(self, query: str, per_page: int = 10) -> list[dict]:
        """搜索机构"""
        params = {"search": query, "per_page": per_page}
        data = self._get("/institutions", params)
        return data.get("results", [])

    @staticmethod
    def extract_paper(raw: dict, search_query: str = "") -> dict:
        """将原始 OpenAlex work JSON 转为标准化论文 schema"""
        # 重建摘要（从倒排索引）
        abstract = reconstruct_abstract(raw.get("abstract_inverted_index"))

        # 提取作者信息
        authors = []
        for authorship in raw.get("authorships", []):
            author = authorship.get("author", {})
            institutions = authorship.get("institutions", [])
            inst_name = institutions[0].get("display_name", "") if institutions else ""
            raw_author_id = author.get("id") or ""
            authors.append({
                "name": author.get("display_name") or "",
                "id": raw_author_id.replace("https://openalex.org/", ""),
                "institution": inst_name,
            })

        # 提取主题
        topics = [t.get("display_name", "") for t in raw.get("topics", [])[:5]]

        # 提取来源（期刊/会议）
        primary_location = raw.get("primary_location") or {}
        source_info = primary_location.get("source") or {}
        source = {
            "name": source_info.get("display_name") or "",
            "id": (source_info.get("id") or "").replace("https://openalex.org/", ""),
            "type": source_info.get("type") or "",
        }

        # Open Access 信息
        open_access = raw.get("open_access") or {}
        best_oa = open_access.get("oa_url") or ""

        # 引用文献
        referenced = raw.get("referenced_works", [])
        referenced_ids = [
            (r or "").replace("https://openalex.org/", "") for r in (referenced or [])
        ]

        # ID 处理
        raw_id = raw.get("id") or ""
        paper_id = raw_id.replace("https://openalex.org/", "") if raw_id else ""

        return {
            "id": paper_id,
            "doi": raw.get("doi", "") or "",
            "title": raw.get("title", "") or "",
            "authors": authors,
            "year": raw.get("publication_year"),
            "citation_count": raw.get("cited_by_count", 0),
            "abstract": abstract,
            "topics": topics,
            "source": source,
            "open_access_url": best_oa,
            "is_oa": open_access.get("is_oa", False),
            "referenced_works": referenced_ids[:50],  # 限制数量
            "search_query": search_query,
            "analysis": None,  # 待 DeepSeek 分析填充
        }


def reconstruct_abstract(inverted_index: Optional[dict]) -> str:
    """从 OpenAlex 倒排索引重建摘要文本"""
    if not inverted_index:
        return ""

    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))

    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)
