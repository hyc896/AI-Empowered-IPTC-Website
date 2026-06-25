# -*- coding: utf-8 -*-

"""
澎湃新闻上海频道采集器
数据来源：https://www.thepaper.cn/channel_25950
特点：Next.js SSR，__NEXT_DATA__ 中包含完整文章列表数据
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

from backend.database.entities import ThepaperShanghaiMessage
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


class ThepaperShanghaiCollector(PlaywrightCollectorBase):
    """澎湃新闻上海频道采集器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.source_id = config.get('id', 'auto')
        self.url = config['config'].get('url', 'https://www.thepaper.cn/channel_25950')
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
            logger.info(f"【澎湃上海】采集器初始化成功")
            return True
        except Exception as e:
            logger.error(f"【澎湃上海】初始化失败: {e}")
            return False

    async def _collect_once(self) -> None:
        try:
            existing_urls = await self._get_existing_urls()
            articles = await self._scrape_articles(existing_urls)
            if not articles:
                logger.debug("【澎湃上海】没有发现新文章")
                return
            logger.info(f"【澎湃上海】抓取到 {len(articles)} 篇新文章")
            await self._preprocess_items(articles)
            await self._store_items(articles)
            logger.info(f"【澎湃上海】采集完成，共处理 {len(articles)} 篇文章")
        except Exception as e:
            logger.error(f"【澎湃上海】采集错误: {e}", exc_info=True)

    async def _get_existing_urls(self, limit: int = 1000) -> set:
        try:
            with create_session() as db:
                results = db.query(ThepaperShanghaiMessage.url).filter(
                    ThepaperShanghaiMessage.source_id == self.source_id,
                    ThepaperShanghaiMessage.url.isnot(None)
                ).order_by(ThepaperShanghaiMessage.crawled_at.desc()).limit(limit).all()
                return {str(row[0]) for row in results if row[0]}
        except Exception as e:
            logger.error(f"【澎湃上海】获取existing_urls失败: {e}")
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

            # 从 __NEXT_DATA__ 提取文章列表
            next_data_text = await page.evaluate(
                "() => { const el = document.getElementById('__NEXT_DATA__'); return el ? el.textContent : null; }"
            )
            if not next_data_text:
                logger.warning("【澎湃上海】未找到 __NEXT_DATA__，尝试滚动加载")
                return await self._scrape_by_scroll(page, existing_urls)

            next_data = json.loads(next_data_text)
            # 实际路径：props.pageProps.data.data.list
            props = next_data.get('props', {}).get('pageProps', {})
            items = props.get('data', {}).get('data', {}).get('list', [])
            if not items:
                # 兼容备用路径
                items = props.get('initData', {}).get('list', props.get('list', []))

            logger.info(f"【澎湃上海】从 __NEXT_DATA__ 获取到 {len(items)} 条数据")

            for item in items:
                if len(articles) >= self.max_articles:
                    break

                cont_id = str(item.get('contId', ''))
                if not cont_id:
                    continue

                article_url = f"https://www.thepaper.cn/newsDetail_forward_{cont_id}"
                if article_url in existing_urls:
                    logger.debug(f"【澎湃上海】已存在，跳过: {article_url}")
                    continue

                title = item.get('name', '').strip()
                if not title:
                    continue

                # 时间处理：pubTimeLong 是毫秒时间戳
                pub_time_long = item.get('pubTimeLong')
                if pub_time_long:
                    published_at = datetime.fromtimestamp(pub_time_long / 1000)
                else:
                    published_at = datetime.now()

                # 获取文章正文
                content = await self._fetch_article_content(page, article_url)
                if not content:
                    logger.warning(f"【澎湃上海】无法获取内容: {article_url}")
                    continue

                summary = content[:200] if len(content) > 200 else content

                articles.append({
                    'external_id': cont_id,
                    'title': title,
                    'content': content,
                    'summary': summary,
                    'url': article_url,
                    'published_at': published_at,
                    'provider': '澎湃新闻',
                    'language': self.language,
                    'category': item.get('nodeName', '上海')
                })
                existing_urls.add(article_url)
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"【澎湃上海】抓取失败: {e}", exc_info=True)
        finally:
            if page:
                await page.close()
        return articles

    async def _scrape_by_scroll(self, page: Page, existing_urls: set) -> List[Dict[str, Any]]:
        """备用：通过DOM选择器抓取"""
        articles = []
        try:
            await page.wait_for_selector('div.ant-card', timeout=10000)
            cards = await page.query_selector_all('div.ant-card')
            for card in cards[:self.max_articles]:
                try:
                    link = await card.query_selector('a')
                    if not link:
                        continue
                    href = await link.get_attribute('href')
                    if not href:
                        continue
                    if href.startswith('/'):
                        href = f'https://www.thepaper.cn{href}'
                    if href in existing_urls:
                        continue
                    title_el = await card.query_selector('h2')
                    title = await title_el.inner_text() if title_el else ''
                    title = title.strip()
                    if not title:
                        continue
                    cont_id_match = re.search(r'newsDetail_forward_(\d+)', href)
                    cont_id = cont_id_match.group(1) if cont_id_match else ''
                    content = await self._fetch_article_content(page, href)
                    if not content:
                        continue
                    articles.append({
                        'external_id': cont_id,
                        'title': title,
                        'content': content,
                        'summary': content[:200],
                        'url': href,
                        'published_at': datetime.now(),
                        'provider': '澎湃新闻',
                        'language': self.language,
                        'category': '上海'
                    })
                    existing_urls.add(href)
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"【澎湃上海】DOM解析失败: {e}")
                    continue
        except Exception as e:
            logger.error(f"【澎湃上海】滚动抓取失败: {e}")
        return articles

    async def _fetch_article_content(self, page: Page, url: str) -> str:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(1)
            for selector in ['.news_txt', '.article-content', '.content', 'article']:
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
            logger.error(f"【澎湃上海】获取正文失败 {url}: {e}")
            return ""

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
                logger.error(f"【澎湃上海】预处理失败 [{idx}]: {e}")
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
                    msg = ThepaperShanghaiMessage(
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
                            logger.error(f"【澎湃上海】MySQL存储错误: {e}")
        except Exception as e:
            logger.error(f"【澎湃上海】MySQL存储失败: {e}")

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
            logger.error(f"【澎湃上海】ChromaDB存储失败: {e}")
