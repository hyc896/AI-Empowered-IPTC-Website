# -*- coding: utf-8 -*-

"""
通用上海本地 HTML 采集器。

面向页面结构相对传统、可用 requests 抓取的上海本地源：
- 上海智慧党建
- 上海党史网
- 新华网上海频道（HTTP）

多个来源共用 mp_shanghai_local_messages，通过 source_id/provider/category 区分。
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError
from urllib3.exceptions import InsecureRequestWarning

from backend.database.connection import create_session
from backend.database.entities import ShanghaiLocalMessage

try:
    from backend.storage import get_chromadb_storage
    _chroma_available = True
except ImportError:
    _chroma_available = False

try:
    from backend.llm import get_embedding_client
    _llm_available = True
except ImportError:
    _llm_available = False

try:
    from backend.services import get_field_enricher
    _field_enricher_available = True
except ImportError:
    _field_enricher_available = False


logger = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

DEFAULT_INCLUDE_KEYWORDS = [
    "上海", "浦东", "黄浦", "徐汇", "长宁", "静安", "普陀", "虹口", "杨浦",
    "闵行", "宝山", "嘉定", "金山", "松江", "青浦", "奉贤", "崇明",
    "党建", "党史", "红色", "基层", "社区", "治理", "初心", "使命",
    "中共", "共产党", "党员", "党支部", "红色文化", "实践", "思政",
]

DEFAULT_CONTENT_SELECTORS = [
    "article",
    ".article",
    ".article-content",
    ".content",
    ".main",
    ".detail",
    ".newInfo",
    ".TRS_Editor",
    "#ivs_content",
    "#detailContent",
    ".rm_txt_con",
    ".text_con",
]


class ShanghaiLocalCollector:
    """requests 模式的上海本地源采集器，不启动浏览器。"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        nested = config.get("config", {})

        self.source_id = config.get("id", "auto")
        self.source_name = config.get("name", "shanghai_local")
        self.display_name = config.get("display_name") or self.source_name
        self.mysql_table = config["mysql_table"]
        self.chroma_collection = config["chroma_collection"]

        configured_urls = nested.get("urls") or [nested.get("url")]
        self.urls = [url for url in configured_urls if url]
        self.base_url = nested.get("base_url") or (self.urls[0] if self.urls else "")
        self.provider = nested.get("provider") or self.display_name
        self.category = nested.get("category") or "上海本地"
        self.region = nested.get("region", "中国/上海")
        self.language = nested.get("language", "zh")
        self.max_articles = int(nested.get("max_articles", 20))
        self.timeout = int(nested.get("request_timeout", 15))
        self.encoding = nested.get("encoding")
        self.include_keywords = nested.get("include_keywords") or DEFAULT_INCLUDE_KEYWORDS
        self.include_url_patterns = nested.get("include_url_patterns") or []
        self.exclude_url_patterns = nested.get("exclude_url_patterns") or [
            "#", "javascript:", "mailto:", "/login", "/register"
        ]

        self.chroma_storage = get_chromadb_storage() if _chroma_available else None
        self.embedding_client = get_embedding_client() if _llm_available else None
        self.field_enricher = get_field_enricher() if _field_enricher_available else None

        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "close",
        })

    async def initialize(self) -> bool:
        try:
            if self.chroma_storage:
                self.chroma_storage.create_collection(collection_name=self.chroma_collection)
            logger.info("【%s】采集器初始化成功（requests模式）", self.display_name)
            return True
        except Exception as e:
            logger.error("【%s】初始化失败: %s", self.display_name, e)
            return False

    async def collect_once(self) -> Dict[str, Any]:
        try:
            existing_urls = await self._get_existing_urls()
            articles = await self._scrape_articles(existing_urls)
            if not articles:
                logger.info("【%s】没有发现新文章", self.display_name)
                return {"collected": 0, "success": True, "error": None}

            await self._preprocess_items(articles)
            stored_count = await self._store_items(articles)
            logger.info("【%s】采集完成，入库 %s 篇", self.display_name, stored_count)
            return {"collected": stored_count, "success": True, "error": None}
        except Exception as e:
            logger.error("【%s】采集失败: %s", self.display_name, e, exc_info=True)
            return {"collected": 0, "success": False, "error": str(e)}

    async def _get_existing_urls(self, limit: int = 3000) -> set:
        try:
            with create_session() as db:
                results = db.query(ShanghaiLocalMessage.url).filter(
                    ShanghaiLocalMessage.source_id == self.source_id,
                    ShanghaiLocalMessage.url.isnot(None),
                ).order_by(ShanghaiLocalMessage.crawled_at.desc()).limit(limit).all()
                return {str(row[0]) for row in results if row[0]}
        except Exception as e:
            logger.error("【%s】获取 existing_urls 失败: %s", self.display_name, e)
            return set()

    async def _scrape_articles(self, existing_urls: set) -> List[Dict[str, Any]]:
        candidates = await self._collect_candidates(existing_urls)
        articles: List[Dict[str, Any]] = []

        for item in candidates:
            if len(articles) >= self.max_articles:
                break

            detail = await self._fetch_article_detail(item["url"])
            if not detail.get("content"):
                continue

            full_text = f"{item['title']}\n{detail.get('summary') or ''}\n{detail['content']}"
            if not self._is_relevant(full_text):
                continue

            articles.append({
                "external_id": item["external_id"],
                "title": item["title"],
                "content": detail["content"],
                "summary": detail.get("summary") or detail["content"][:200],
                "url": item["url"],
                "published_at": detail.get("published_at") or item.get("published_at") or datetime.now(),
                "provider": self.provider,
                "language": self.language,
                "category": self.category,
                "metadata": {
                    "source_name": self.source_name,
                    "list_url": item.get("list_url"),
                },
            })
            existing_urls.add(item["url"])
            await asyncio.sleep(0.2)

        return articles

    async def _collect_candidates(self, existing_urls: set) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        seen = set(existing_urls)

        for list_url in self.urls:
            try:
                html = await self._request_text(list_url)
                soup = BeautifulSoup(html, "html.parser")
                found = 0

                for a in soup.find_all("a", href=True):
                    title = self._clean_text(a.get_text(" ", strip=True))
                    href = self._normalize_url(a["href"], list_url)
                    if not title or len(title) < 6 or not href:
                        continue
                    if href in seen or not self._url_allowed(href):
                        continue
                    if not self._is_relevant(title) and not self._matches_url_patterns(href):
                        continue

                    seen.add(href)
                    candidates.append({
                        "url": href,
                        "title": title,
                        "external_id": self._external_id_from_url(href),
                        "published_at": self._parse_date_from_text(f"{href} {title}"),
                        "list_url": list_url,
                    })
                    found += 1
                    if len(candidates) >= self.max_articles * 3:
                        break

                logger.info("【%s】从 %s 收集到 %s 条候选", self.display_name, list_url, found)
            except Exception as e:
                logger.error("【%s】列表页抓取失败 %s: %s", self.display_name, list_url, e)

        return candidates

    async def _fetch_article_detail(self, url: str) -> Dict[str, Any]:
        try:
            html = await self._request_text(url)
            soup = BeautifulSoup(html, "html.parser")
            content = self._extract_content(soup)
            title_text = soup.get_text("\n", strip=True)[:2000]
            return {
                "content": content,
                "summary": self._extract_summary(soup),
                "published_at": self._parse_date_from_text(title_text + "\n" + url),
            }
        except Exception as e:
            logger.warning("【%s】正文抓取失败 %s: %s", self.display_name, url, e)
            return {}

    async def _request_text(self, url: str) -> str:
        def _get() -> str:
            resp = self._session.get(url, timeout=self.timeout, verify=False)
            resp.raise_for_status()
            if self.encoding:
                resp.encoding = self.encoding
            else:
                resp.encoding = resp.apparent_encoding or resp.encoding
            return resp.text

        return await asyncio.get_event_loop().run_in_executor(None, _get)

    def _extract_content(self, soup: BeautifulSoup) -> str:
        for selector in DEFAULT_CONTENT_SELECTORS:
            node = soup.select_one(selector)
            if not node:
                continue
            text = self._extract_paragraph_text(node)
            if len(text) >= 80:
                return text

        paragraphs = [
            self._clean_text(p.get_text(" ", strip=True))
            for p in soup.find_all("p")
        ]
        paragraphs = [p for p in paragraphs if len(p) >= 12]
        return "\n\n".join(paragraphs)

    def _extract_paragraph_text(self, node) -> str:
        paragraphs = [self._clean_text(p.get_text(" ", strip=True)) for p in node.find_all("p")]
        paragraphs = [p for p in paragraphs if len(p) >= 12]
        if paragraphs:
            return "\n\n".join(paragraphs)
        return self._clean_text(node.get_text("\n", strip=True))

    def _extract_summary(self, soup: BeautifulSoup) -> Optional[str]:
        meta = soup.find("meta", attrs={"name": re.compile("description", re.I)})
        if meta and meta.get("content"):
            summary = self._clean_text(meta["content"])
            if summary:
                return summary[:500]
        return None

    def _normalize_url(self, href: str, list_url: str) -> Optional[str]:
        href = (href or "").strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:")):
            return None
        url = urljoin(list_url, href)
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return None
        return url.split("#", 1)[0]

    def _url_allowed(self, url: str) -> bool:
        lower = url.lower()
        if any(pattern.lower() in lower for pattern in self.exclude_url_patterns):
            return False
        if self.include_url_patterns:
            return self._matches_url_patterns(url)
        return True

    def _matches_url_patterns(self, url: str) -> bool:
        lower = url.lower()
        return any(pattern.lower() in lower for pattern in self.include_url_patterns)

    def _is_relevant(self, text: str) -> bool:
        if not self.include_keywords:
            return True
        return any(keyword in text for keyword in self.include_keywords)

    def _external_id_from_url(self, url: str) -> str:
        match = re.search(r"(?:articleid=|content/|/)([0-9a-fA-F-]{16,}|[A-Za-z0-9_-]{8,})(?:\.html|/c\.html|$)", url)
        if match:
            return match.group(1)[:190]
        return hashlib.md5(url.encode("utf-8")).hexdigest()

    def _parse_date_from_text(self, text: str) -> Optional[datetime]:
        patterns = [
            r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})",
            r"/(20\d{2})(\d{2})(\d{2})/",
            r"/(20\d{2})(\d{2})(\d{2})[a-zA-Z0-9_-]*/",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            try:
                year, month, day = [int(part) for part in match.groups()[:3]]
                return datetime(year, month, day)
            except Exception:
                continue
        return None

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    async def _preprocess_items(self, items: List[Dict[str, Any]]) -> None:
        for idx, item in enumerate(items, 1):
            item["message_id"] = str(uuid.uuid4())
            try:
                if self.field_enricher:
                    enriched = await self.field_enricher.enrich_fields(
                        title=item["title"], content=item["content"], message_id=item["message_id"]
                    )
                    item["region"] = enriched.get("region") or self.region
                    item["industry_tags"] = enriched.get("industry_tags")
                    item["ai_tag"] = enriched.get("ai_tag")
                else:
                    item["region"] = self.region
                    item["industry_tags"] = None
                    item["ai_tag"] = None
            except Exception as e:
                logger.error("【%s】字段增强失败 [%s]: %s", self.display_name, idx, e)
                item["region"] = self.region
                item["industry_tags"] = None
                item["ai_tag"] = None

    async def _store_items(self, items: List[Dict[str, Any]]) -> int:
        stored = await self._store_to_mysql(items)
        await self._store_to_chroma(items)
        return stored

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> int:
        stored = 0
        try:
            with create_session() as db:
                for item in items:
                    msg = ShanghaiLocalMessage(
                        id=item.get("message_id", str(uuid.uuid4())),
                        source_id=self.source_id,
                        external_id=item.get("external_id"),
                        title=item["title"],
                        content=item["content"],
                        summary=item.get("summary"),
                        provider=item.get("provider") or self.provider,
                        published_at=item.get("published_at"),
                        crawled_at=datetime.now(),
                        url=item["url"],
                        region=item.get("region") or self.region,
                        industry_tags=item.get("industry_tags"),
                        ai_tag=item.get("ai_tag"),
                        category=item.get("category") or self.category,
                        language=item.get("language") or self.language,
                        extra_metadata=item.get("metadata"),
                    )
                    try:
                        db.add(msg)
                        db.commit()
                        stored += 1
                    except IntegrityError as e:
                        db.rollback()
                        if "Duplicate entry" not in str(e):
                            logger.error("【%s】MySQL存储错误: %s", self.display_name, e)
        except Exception as e:
            logger.error("【%s】MySQL存储失败: %s", self.display_name, e)
        return stored

    async def _store_to_chroma(self, items: List[Dict[str, Any]]) -> None:
        if not self.chroma_storage or not self.embedding_client:
            return
        try:
            for item in items:
                doc = f"{item['title']} {item.get('summary', '')}"
                embedding = self.embedding_client.generate_embedding(doc)
                chroma_id = item.get("external_id") or str(uuid.uuid4())
                self.chroma_storage.upsert(
                    collection_name=self.chroma_collection,
                    ids=[chroma_id],
                    documents=[doc],
                    metadatas=[{
                        "source_id": self.source_id,
                        "external_id": item.get("external_id", ""),
                        "published_at": item["published_at"].isoformat() if item.get("published_at") else "",
                        "url": item.get("url", ""),
                        "title": item["title"],
                        "region": item.get("region", ""),
                        "provider": item.get("provider", ""),
                        "language": item.get("language", ""),
                    }],
                    embeddings=[embedding],
                )
        except Exception as e:
            logger.error("【%s】ChromaDB存储失败: %s", self.display_name, e)
