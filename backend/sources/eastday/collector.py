# -*- coding: utf-8 -*-

"""
东方网采集器
数据来源：https://mini.eastday.com/
特点：信息流页面，通过滚动加载，文章链接指向 j.eastday.com
"""

import uuid
import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import Browser, Page
from sqlalchemy.exc import IntegrityError

from backend.database.entities import EastdayMessage
from backend.database.connection import create_session
from backend.collectors.base import PlaywrightCollectorBase

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


class EastdayCollector(PlaywrightCollectorBase):
    """东方网采集器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.source_id = config.get('id', 'auto')
        self.url = config['config'].get('url', 'https://mini.eastday.com/')
        self.region = config['config'].get('region', '中国/上海')
        self.language = config['config'].get('language', 'zh')
        self.max_articles = config['config'].get('max_articles', 20)

        self.chroma_storage = get_chromadb_storage() if _chroma_available else None
        self.embedding_client = get_embedding_client() if _llm_available else None
        self.field_enricher = get_field_enricher() if _field_enricher_available else None

    async def _on_initialize(self) -> bool:
        try:
            if self.chroma_storage:
                self.chroma_storage.create_collection(collection_name=self.chroma_collection)
            logger.info(f"【东方网】采集器初始化成功")
            return True
        except Exception as e:
            logger.error(f"【东方网】初始化失败: {e}")
            return False

    async def _collect_once(self) -> None:
        try:
            existing_urls = await self._get_existing_urls()
            articles = await self._scrape_articles(existing_urls)
            if not articles:
                logger.debug("【东方网】没有发现新文章")
                return
            logger.info(f"【东方网】抓取到 {len(articles)} 篇新文章")
            await self._preprocess_items(articles)
            await self._store_items(articles)
            logger.info(f"【东方网】采集完成，共处理 {len(articles)} 篇文章")
        except Exception as e:
            logger.error(f"【东方网】采集错误: {e}", exc_info=True)

    async def _get_existing_urls(self, limit: int = 1000) -> set:
        try:
            with create_session() as db:
                results = db.query(EastdayMessage.url).filter(
                    EastdayMessage.source_id == self.source_id,
                    EastdayMessage.url.isnot(None)
                ).order_by(EastdayMessage.crawled_at.desc()).limit(limit).all()
                return {str(row[0]) for row in results if row[0]}
        except Exception as e:
            logger.error(f"【东方网】获取existing_urls失败: {e}")
            return set()

    async def _scrape_articles(self, existing_urls: set) -> List[Dict[str, Any]]:
        page: Optional[Page] = None
        articles = []
        try:
            page = await self._browser.new_page()
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            })
            await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)

            # 阶段1：滚动加载，用 JS 批量提取所有链接数据（纯数据，不持有 ElementHandle）
            candidates = await self._collect_candidates(page, existing_urls)
            logger.info(f"【东方网】收集到 {len(candidates)} 条候选链接")

            # 阶段2：逐个抓取正文（此时列表页已不需要，handle 不会失效）
            for item in candidates:
                if len(articles) >= self.max_articles:
                    break
                content = await self._fetch_article_content(page, item['url'])
                if not content:
                    logger.warning(f"【东方网】无法获取内容: {item['url']}")
                    continue
                articles.append({
                    'external_id': item['external_id'],
                    'title': item['title'],
                    'content': content,
                    'summary': content[:200],
                    'url': item['url'],
                    'published_at': item['published_at'],
                    'provider': item['provider'],
                    'language': self.language,
                    'category': '上海'
                })
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"【东方网】抓取失败: {e}", exc_info=True)
        finally:
            if page:
                await page.close()
        return articles

    async def _collect_candidates(self, page, existing_urls: set) -> List[Dict[str, Any]]:
        """
        阶段1：在列表页滚动加载，用 JS evaluate 批量提取链接数据。
        全程不持有 ElementHandle，避免跨导航失效。
        """
        candidates = []
        load_attempts = 0
        max_attempts = 8
        seen_urls = set(existing_urls)

        while load_attempts < max_attempts and len(candidates) < self.max_articles:
            # 用 JS 一次性提取当前页面所有条目的数据
            raw_items = await page.evaluate("""
                () => {
                    const results = [];
                    const selectors = ['li.news-list-item', 'li[class*="news-list"]', '.news-item'];
                    let items = [];
                    for (const sel of selectors) {
                        items = document.querySelectorAll(sel);
                        if (items.length > 0) break;
                    }
                    items.forEach(item => {
                        const linkEl = item.querySelector('a.link') || item.querySelector('a[href*="eastday"]') || item.querySelector('a');
                        if (!linkEl) return;
                        const href = linkEl.getAttribute('href') || '';
                        if (!href || href === '#') return;
                        const titleEl = item.querySelector('a.link') || item.querySelector('.title') || item.querySelector('h3') || item.querySelector('h4');
                        const title = (titleEl ? titleEl.innerText : linkEl.innerText || '').trim();
                        if (!title) return;
                        const timeEl = item.querySelector('span.footer-bar-action') || item.querySelector('.time') || item.querySelector('.date');
                        const timeText = timeEl ? timeEl.innerText.trim() : '';
                        const sourceEl = item.querySelector('a.source') || item.querySelector('.source');
                        const source = sourceEl ? sourceEl.innerText.trim() : '东方网';
                        results.push({href, title, timeText, source});
                    });
                    return results;
                }
            """)

            new_found = 0
            for raw in raw_items:
                href = raw.get('href', '')
                if not href.startswith('http'):
                    href = f'https://mini.eastday.com{href}'
                if href in seen_urls:
                    continue
                seen_urls.add(href)
                candidates.append({
                    'url': href,
                    'title': raw.get('title', ''),
                    'published_at': self._parse_time(raw.get('timeText', '')),
                    'provider': raw.get('source', '东方网') or '东方网',
                    'external_id': self._extract_id(href),
                })
                new_found += 1
                if len(candidates) >= self.max_articles:
                    break

            if new_found == 0:
                break

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(3)
            load_attempts += 1

        return candidates

    async def _fetch_article_content(self, page: Page, url: str) -> str:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(1)
            for selector in ['.article-content', '.content', '.news-content', 'article', '.text']:
                el = await page.query_selector(selector)
                if el:
                    paragraphs = await el.query_selector_all('p')
                    if paragraphs:
                        texts = [await p.inner_text() for p in paragraphs]
                        texts = [t.strip() for t in texts if t.strip()]
                        if texts:
                            return '\n\n'.join(texts)
                    text = await el.inner_text()
                    if text and text.strip():
                        return text.strip()
            return ""
        except Exception as e:
            logger.error(f"【东方网】获取正文失败 {url}: {e}")
            return ""

    def _extract_id(self, url: str) -> str:
        import hashlib
        match = re.search(r'/p/([a-zA-Z0-9_-]+)', url)
        if match:
            return match.group(1)
        match = re.search(r'[?&]id=([^&]+)', url)
        if match:
            return match.group(1)
        return hashlib.md5(url.encode()).hexdigest()[:16]

    def _parse_time(self, time_str: str) -> datetime:
        try:
            now = datetime.now()
            if '分钟前' in time_str:
                mins = int(re.search(r'(\d+)', time_str).group(1))
                return datetime(now.year, now.month, now.day, now.hour, now.minute - mins % 60)
            if '小时前' in time_str:
                hours = int(re.search(r'(\d+)', time_str).group(1))
                return datetime(now.year, now.month, now.day, max(0, now.hour - hours))
            if '昨天' in time_str:
                from datetime import timedelta
                return now - timedelta(days=1)
            from dateutil import parser
            return parser.parse(time_str, fuzzy=True)
        except Exception:
            return datetime.now()

    async def _preprocess_items(self, items: List[Dict[str, Any]]) -> None:
        for idx, item in enumerate(items, 1):
            item['message_id'] = str(uuid.uuid4())
            try:
                if self.field_enricher:
                    enriched = await self.field_enricher.enrich_fields(
                        title=item['title'], content=item['content'], message_id=item['message_id']
                    )
                    item['region'] = enriched.get('region', self.region)
                    item['industry_tags'] = enriched.get('industry_tags')
                    item['ai_tag'] = enriched.get('ai_tag')
                else:
                    item['region'] = self.region
                    item['industry_tags'] = None
                    item['ai_tag'] = None
            except Exception as e:
                logger.error(f"【东方网】预处理失败 [{idx}]: {e}")
                item['region'] = self.region
                item['industry_tags'] = None
                item['ai_tag'] = None

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        await self._store_to_mysql(items)
        await self._store_to_chroma(items)

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> None:
        try:
            with create_session() as db:
                for item in items:
                    msg = EastdayMessage(
                        id=item.get('message_id', str(uuid.uuid4())),
                        source_id=self.source_id,
                        external_id=item.get('external_id'),
                        title=item['title'],
                        content=item['content'],
                        summary=item.get('summary'),
                        provider=item.get('provider'),
                        published_at=item.get('published_at'),
                        crawled_at=datetime.now(),
                        url=item['url'],
                        region=item.get('region'),
                        industry_tags=item.get('industry_tags'),
                        ai_tag=item.get('ai_tag'),
                        category=item.get('category'),
                        language=item.get('language')
                    )
                    try:
                        db.add(msg)
                        db.commit()
                    except IntegrityError as e:
                        db.rollback()
                        if "Duplicate entry" not in str(e):
                            logger.error(f"【东方网】MySQL存储错误: {e}")
        except Exception as e:
            logger.error(f"【东方网】MySQL存储失败: {e}")

    async def _store_to_chroma(self, items: List[Dict[str, Any]]) -> None:
        if not self.chroma_storage or not self.embedding_client:
            return
        try:
            for item in items:
                doc = f"{item['title']} {item.get('summary', '')}"
                embedding = self.embedding_client.generate_embedding(doc)
                chroma_id = item.get('external_id') or str(uuid.uuid4())
                self.chroma_storage.upsert(
                    collection_name=self.chroma_collection,
                    ids=[chroma_id],
                    documents=[doc],
                    metadatas=[{
                        "source_id": self.source_id,
                        "external_id": item.get('external_id', ''),
                        "published_at": item['published_at'].isoformat() if item.get('published_at') else '',
                        "url": item.get('url', ''),
                        "title": item['title'],
                        "region": item.get('region', ''),
                        "language": item.get('language', '')
                    }],
                    embeddings=[embedding]
                )
        except Exception as e:
            logger.error(f"【东方网】ChromaDB存储失败: {e}")
