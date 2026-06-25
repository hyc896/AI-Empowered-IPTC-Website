# -*- coding: utf-8 -*-

"""
上观新闻采集器（同时覆盖解放日报，两者为同一站点）
数据来源：https://www.shobserver.com/
特点：数据通过 JSON API 接口加载，需要请求 API 获取文章列表
"""

import json
import uuid
import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import Browser, Page
from sqlalchemy.exc import IntegrityError

from backend.database.entities import ShanghaiObserverMessage
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


class ShanghaiObserverCollector(PlaywrightCollectorBase):
    """上观新闻采集器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.source_id = config.get('id', 'auto')
        self.url = config['config'].get('url', 'https://www.shobserver.com/')
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
            logger.info(f"【上观新闻】采集器初始化成功")
            return True
        except Exception as e:
            logger.error(f"【上观新闻】初始化失败: {e}")
            return False

    async def _collect_once(self) -> None:
        try:
            existing_urls = await self._get_existing_urls()
            articles = await self._scrape_articles(existing_urls)
            if not articles:
                logger.debug("【上观新闻】没有发现新文章")
                return
            logger.info(f"【上观新闻】抓取到 {len(articles)} 篇新文章")
            await self._preprocess_items(articles)
            await self._store_items(articles)
            logger.info(f"【上观新闻】采集完成，共处理 {len(articles)} 篇文章")
        except Exception as e:
            logger.error(f"【上观新闻】采集错误: {e}", exc_info=True)

    async def _get_existing_urls(self, limit: int = 1000) -> set:
        try:
            with create_session() as db:
                results = db.query(ShanghaiObserverMessage.url).filter(
                    ShanghaiObserverMessage.source_id == self.source_id,
                    ShanghaiObserverMessage.url.isnot(None)
                ).order_by(ShanghaiObserverMessage.crawled_at.desc()).limit(limit).all()
                return {str(row[0]) for row in results if row[0]}
        except Exception as e:
            logger.error(f"【上观新闻】获取existing_urls失败: {e}")
            return set()

    async def _scrape_articles(self, existing_urls: set) -> List[Dict[str, Any]]:
        page: Optional[Page] = None
        articles = []
        try:
            page = await self._browser.new_page()
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Referer': 'https://www.shobserver.com/',
            })

            # 先访问首页（建立 cookie/session）
            await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)

            # 直接请求已知的 JSON API（DATA_BASE_PATH = /staticsg/data/）
            items = []
            json_urls = [
                'https://www.shobserver.com/staticsg/data/web/home/recommandnewslist.json',
                'https://www.shobserver.com/staticsg/data/web/home/topnewslist.json',
                'https://www.shobserver.com/staticsg/data/web/home/quicknewslist.json',
            ]
            for json_url in json_urls:
                try:
                    resp = await page.evaluate(f"""
                        async () => {{
                            const r = await fetch('{json_url}', {{headers: {{'Referer': 'https://www.shobserver.com/'}}}});
                            if (!r.ok) return null;
                            return await r.json();
                        }}
                    """)
                    if resp:
                        raw = resp.get('data', resp) if isinstance(resp, dict) else resp
                        if isinstance(raw, list):
                            items.extend(raw)
                except Exception as e:
                    logger.debug(f"【上观新闻】API请求失败 {json_url}: {e}")

            # 如果 API 方式失败，降级为 DOM 解析
            if not items:
                logger.info("【上观新闻】API方式失败，降级为DOM解析")
                items = await self._scrape_by_dom(page)

            logger.info(f"【上观新闻】获取到 {len(items)} 条原始数据")

            for item in items:
                if len(articles) >= self.max_articles:
                    break

                # 兼容不同的字段名
                article_id = str(item.get('id', item.get('newsId', item.get('nid', ''))))
                title = str(item.get('title', item.get('name', ''))).strip()
                if not title or not article_id:
                    continue

                article_url = f"https://www.shobserver.com/staticsg/res/html/web/newsDetail.html?id={article_id}&sid=11"
                if article_url in existing_urls:
                    continue

                # 时间处理
                pub_time = item.get('publishtime', item.get('pubtime', item.get('time', '')))
                published_at = self._parse_time(str(pub_time)) if pub_time else datetime.now()

                content = await self._fetch_article_content(page, article_url, article_id)
                if not content:
                    logger.warning(f"【上观新闻】无法获取内容: {article_url}")
                    continue

                articles.append({
                    'external_id': article_id,
                    'title': title,
                    'content': content,
                    'summary': content[:200],
                    'url': article_url,
                    'published_at': published_at,
                    'provider': '上观新闻',
                    'language': self.language,
                    'category': item.get('channelName', item.get('column', '上海'))
                })
                existing_urls.add(article_url)
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"【上观新闻】抓取失败: {e}", exc_info=True)
        finally:
            if page:
                await page.close()
        return articles

    async def _scrape_by_dom(self, page: Page) -> List[Dict]:
        """DOM降级解析：从页面链接中提取文章ID"""
        items = []
        try:
            links = await page.query_selector_all('a[href*="newsDetail"]')
            seen_ids = set()
            for link in links:
                href = await link.get_attribute('href') or ''
                id_match = re.search(r'[?&]id=(\d+)', href)
                if not id_match:
                    continue
                article_id = id_match.group(1)
                if article_id in seen_ids:
                    continue
                seen_ids.add(article_id)
                title_el = await link.query_selector('span, p, h3, h4')
                title = await title_el.inner_text() if title_el else await link.inner_text()
                title = title.strip()
                if title:
                    items.append({'id': article_id, 'title': title})
        except Exception as e:
            logger.error(f"【上观新闻】DOM解析失败: {e}")
        return items

    async def _fetch_article_content(self, page: Page, url: str, article_id: str) -> str:
        """获取文章正文，优先通过 API 接口"""
        try:
            # 尝试通过 API 获取正文
            api_url = f"https://www.shobserver.com/api/news/getNewsDetail?id={article_id}"
            content_data = await page.evaluate(f"""
                async () => {{
                    try {{
                        const r = await fetch('{api_url}', {{headers: {{'Referer': 'https://www.shobserver.com/'}}}});
                        if (!r.ok) return null;
                        return await r.json();
                    }} catch(e) {{ return null; }}
                }}
            """)
            if content_data:
                content = content_data.get('data', {}).get('content', '') or content_data.get('content', '')
                if content:
                    # 去除HTML标签
                    content = re.sub(r'<[^>]+>', '', content)
                    content = re.sub(r'\s+', ' ', content).strip()
                    if content:
                        return content

            # 降级：直接访问页面
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            for selector in ['.article-content', '.content-text', '.news-content', '.content', 'article']:
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
            logger.error(f"【上观新闻】获取正文失败 {url}: {e}")
            return ""

    def _parse_time(self, time_str: str) -> datetime:
        try:
            # 时间戳（毫秒）
            if time_str.isdigit() and len(time_str) > 10:
                return datetime.fromtimestamp(int(time_str) / 1000)
            # 时间戳（秒）
            if time_str.isdigit():
                return datetime.fromtimestamp(int(time_str))
            # 标准格式
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
                logger.error(f"【上观新闻】预处理失败 [{idx}]: {e}")
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
                    msg = ShanghaiObserverMessage(
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
                            logger.error(f"【上观新闻】MySQL存储错误: {e}")
        except Exception as e:
            logger.error(f"【上观新闻】MySQL存储失败: {e}")

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
            logger.error(f"【上观新闻】ChromaDB存储失败: {e}")
