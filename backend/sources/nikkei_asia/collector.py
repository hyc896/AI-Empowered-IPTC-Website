# -*- coding: utf-8 -*-

"""
Nikkei Asia AI News Collector
日经亚洲人工智能板块采集器
"""

import re
import json
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright
from sqlalchemy.exc import IntegrityError

from backend.database.entities import NikkeiAsiaAIMessage
from backend.database.connection import create_session

try:
    from backend.storage import get_chromadb_storage
    _chroma_available = True
except ImportError:
    _chroma_available = False

try:
    from backend.llm import get_embedding_client, get_translator
    _llm_available = True
except ImportError:
    _llm_available = False

try:
    from backend.services import get_field_enricher
    _field_enricher_available = True
except ImportError:
    _field_enricher_available = False

logger = logging.getLogger(__name__)


class NikkeiAsiaCollector:
    """日经亚洲AI新闻采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - url: 日经亚洲AI板块URL
                - source_id: 消息源ID
        """
        self.config = config
        self.interval = config.get('interval', 3600)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.url = config['config'].get('url', 'https://asia.nikkei.com/Business/Technology/Artificial-intelligence')
        self.source_id = config.get('id', 'auto')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【Nikkei Asia】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【Nikkei Asia】LLM服务不可用，将跳过向量化和翻译")

        if _field_enricher_available:
            self.field_enricher = get_field_enricher()
        else:
            self.field_enricher = None
            logger.warning("【Nikkei Asia】字段增强服务不可用")

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._running = False

    async def initialize(self) -> bool:
        """初始化采集器（启动Playwright浏览器）"""
        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )

            if self.chroma_storage:
                self.chroma_storage.create_collection(
                    collection_name=self.chroma_collection
                )

            logger.info(f"【Nikkei Asia】采集器初始化成功: {self.url}")
            return True
        except Exception as e:
            logger.error(f"【Nikkei Asia】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """主循环：定时采集"""
        if not await self.initialize():
            logger.error("【Nikkei Asia】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【Nikkei Asia】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【Nikkei Asia】采集失败: {e}", exc_info=True)

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        await self._close_browser()
        logger.info("【Nikkei Asia】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新消息的URL
        2. Playwright爬取列表页，解析嵌入的JSON数据
        3. 过滤已存在的URL
        4. 预翻译：批量翻译summary
        5. 存储到MySQL + ChromaDB
        """
        try:
            latest_url = await self._get_latest_stored_url()
            logger.debug(f"Latest stored URL: {latest_url}")

            articles = await self._scrape_articles()

            if not articles:
                logger.debug("No articles found")
                return

            new_articles = self._filter_new_articles(articles, latest_url)

            if new_articles:
                enriched_articles = await self._pre_translate(new_articles)
                await self._store_items(enriched_articles)
                logger.info(f"【Nikkei Asia】采集到 {len(new_articles)} 条新文章")
            else:
                logger.debug("【Nikkei Asia】所有文章已存在，无新数据")

        except Exception as e:
            logger.error(f"【Nikkei Asia】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """获取MySQL中最新文章的URL"""
        try:
            with create_session() as db:
                latest = db.query(NikkeiAsiaAIMessage).order_by(
                    NikkeiAsiaAIMessage.crawled_at.desc()
                ).first()

                if latest and latest.url:
                    logger.debug(f"Latest stored: url={latest.url}, crawled_at={latest.crawled_at}")
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL: {e}")
            return None

    async def _scrape_articles(self, max_pages: int = 21) -> List[Dict[str, Any]]:
        """
        爬取文章列表（支持分页，从嵌入的JSON数据中提取）

        Args:
            max_pages: 最多爬取的页数（默认21页）

        Returns:
            所有页面的文章列表
        """
        all_articles = []

        for page_num in range(1, max_pages + 1):
            page_url = f"{self.url}?page={page_num}" if page_num > 1 else self.url

            logger.info(f"【Nikkei Asia】正在采集第 {page_num}/{max_pages} 页...")

            page_articles = await self._scrape_single_page(page_url)

            if not page_articles:
                logger.warning(f"【Nikkei Asia】第 {page_num} 页未获取到文章，停止采集")
                break

            all_articles.extend(page_articles)
            logger.info(f"【Nikkei Asia】第 {page_num} 页采集到 {len(page_articles)} 条文章，累计 {len(all_articles)} 条")

            # 礼貌延迟，避免请求过快
            await asyncio.sleep(2)

        logger.info(f"【Nikkei Asia】总共采集到 {len(all_articles)} 条文章")
        return all_articles

    async def _scrape_single_page(self, page_url: str) -> List[Dict[str, Any]]:
        """
        爬取单个页面的文章列表

        Args:
            page_url: 页面URL

        Returns:
            该页面的文章列表
        """
        page: Optional[Page] = None
        context = None
        try:
            context = await self._browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()

            await page.goto(page_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

            content = await page.content()

            json_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', content, re.DOTALL)

            if not json_match:
                logger.error(f"未找到嵌入的JSON数据: {page_url}")
                return []

            json_data = json.loads(json_match.group(1))

            articles_raw = json_data.get('props', {}).get('pageProps', {}).get('data', {}).get('stream', [])

            articles = []
            for item in articles_raw:
                try:
                    article_data = self._parse_article_data(item)
                    if article_data:
                        articles.append(article_data)
                except Exception as e:
                    logger.error(f"Failed to parse article: {e}")
                    continue

            return articles

        except Exception as e:
            logger.error(f"Failed to scrape page {page_url}: {e}", exc_info=True)
            return []
        finally:
            if page:
                await page.close()
            if context:
                await context.close()

    def _parse_article_data(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析单条文章数据

        Args:
            item: JSON中的文章对象

        Returns:
            文章数据字典
        """
        try:
            path = item.get('path', '') or item.get('url', '')
            if not path:
                return None

            url = f"https://asia.nikkei.com{path}"

            external_id = item.get('id', '') or path.split('/')[-1]

            title = item.get('headline', '')
            if not title:
                return None

            content = item.get('subhead', '') or title

            display_date = item.get('displayDate')
            if display_date and isinstance(display_date, (int, float)):
                published_at = datetime.fromtimestamp(display_date)
            else:
                published_at = datetime.now()

            author_data = item.get('author')
            provider = None
            if author_data and isinstance(author_data, dict):
                provider = author_data.get('name')

            return {
                "external_id": str(external_id),
                "title": title.strip(),
                "content": content.strip(),
                "published_at": published_at,
                "url": url,
                "provider": provider
            }
        except Exception as e:
            logger.error(f"Failed to parse article data: {e}")
            return None

    def _filter_new_articles(
        self,
        articles: List[Dict[str, Any]],
        latest_url: Optional[str]
    ) -> List[Dict[str, Any]]:
        """过滤已存在的文章"""
        if not latest_url:
            return articles

        new_articles = []
        for article in articles:
            if article.get('url') == latest_url:
                break
            new_articles.append(article)

        return new_articles

    async def _pre_translate(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        预翻译模式：在数据库事务外批量翻译summary

        Args:
            articles: 文章列表

        Returns:
            增强后的文章列表（添加了summary_zh字段）
        """
        if not self.translator:
            for article in articles:
                article['summary_zh'] = None
            return articles

        logger.debug(f"【Nikkei Asia】批量翻译 {len(articles)} 条文章摘要")

        for article in articles:
            try:
                content = article['content']
                if len(content) > 1000:
                    content = content[:1000]

                summary_zh = await self.translator.translate(content)
                article['summary_zh'] = summary_zh

            except Exception as e:
                logger.error(f"【Nikkei Asia】翻译失败: {e}")
                article['summary_zh'] = content[:1000] if len(content) > 1000 else content

        return articles

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        """并发存储到MySQL和ChromaDB"""
        mysql_task = self._store_to_mysql(items)
        chroma_task = self._store_to_chroma(items)
        await asyncio.gather(mysql_task, chroma_task, return_exceptions=True)

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> None:
        """存储到MySQL（预增强模式：在事务外完成字段增强）"""
        try:
            # 预增强：在数据库事务外批量增强字段
            if self.field_enricher:
                logger.debug(f"【Nikkei Asia】批量增强 {len(items)} 条消息字段")
                for item in items:
                    try:
                        enriched = await self.field_enricher.enrich_fields(
                            title=item['title'],
                            content=item['content']
                        )
                        item['region'] = enriched.get('region')
                        item['industry_tags'] = enriched.get('industry_tags')
                        item['ai_tag'] = enriched.get('ai_tag')
                    except Exception as e:
                        logger.error(f"【Nikkei Asia】字段增强失败: {e}")
                        item['region'] = None
                        item['industry_tags'] = None
                        item['ai_tag'] = None

            with create_session() as db:
                for item in items:
                    content = item['content']
                    summary = item.get('summary_zh') or (content if len(content) <= 1000 else content[:1000])

                    message = NikkeiAsiaAIMessage(
                        id=str(uuid.uuid4()),
                        source_id=self.source_id,
                        external_id=item.get('external_id'),
                        title=item['title'],
                        content=content,
                        summary=summary,
                        provider=item.get('provider'),
                        published_at=item.get('published_at'),
                        url=item['url'],
                        region=item.get('region'),
                        category='Artificial Intelligence',
                        language='en',
                        industry_tags=item.get('industry_tags'),
                        ai_tag=item.get('ai_tag'),
                        crawled_at=datetime.now()
                    )

                    try:
                        db.add(message)
                        db.commit()
                        logger.debug(f"Inserted to MySQL: url={item['url']}")
                    except IntegrityError as e:
                        db.rollback()
                        if "Duplicate entry" in str(e):
                            logger.debug(f"Duplicate URL: {item['url']}")
                        else:
                            logger.error(f"MySQL insert error: {e}")
        except Exception as e:
            logger.error(f"Failed to store to MySQL: {e}", exc_info=True)

    async def _store_to_chroma(self, items: List[Dict[str, Any]]) -> None:
        """存储到ChromaDB"""
        if not self.chroma_storage or not self.embedding_client:
            return

        try:
            for item in items:
                summary = item.get('summary_zh') or item['content']
                document_text = f"{item['title']} {summary}"

                embedding = self.embedding_client.generate_embedding(document_text)

                chroma_id = item.get('external_id') or item.get('url') or str(uuid.uuid4())

                self.chroma_storage.upsert(
                    collection_name=self.chroma_collection,
                    ids=[str(chroma_id)],
                    documents=[document_text],
                    metadatas=[{
                        "source_id": self.source_id,
                        "provider": item.get('provider', ''),
                        "published_at": item['published_at'].isoformat() if item.get('published_at') else '',
                        "url": item['url'],
                        "title": item['title']
                    }],
                    embeddings=[embedding]
                )
                logger.debug(f"Inserted to ChromaDB: external_id={item.get('external_id')}")
        except Exception as e:
            logger.error(f"Failed to store to ChromaDB: {e}", exc_info=True)

    async def _close_browser(self) -> None:
        """关闭浏览器"""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.error(f"Failed to close browser: {e}")
