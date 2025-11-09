# -*- coding: utf-8 -*-

"""
Kr36 Collector
36氪快讯独立采集器
"""

import re
import uuid
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, parse_qs, unquote
from playwright.async_api import async_playwright, Browser, Page, Playwright
from sqlalchemy.exc import IntegrityError

from backend.database.entities import Kr36Message
from backend.database.connection import create_session
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

logger = logging.getLogger(__name__)


class Kr36Collector:
    """36氪快讯独立采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - url: 36氪快讯URL
                - source_id: 消息源ID（关联message_sources表）
        """
        self.config = config
        self.interval = config.get('interval', 180)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.url = config['config'].get('url', 'https://www.36kr.com/newsflashes')
        self.source_id = config.get('id', 'auto')

        # 优雅地处理缺失的依赖
        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【36氪】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
        else:
            self.embedding_client = None
            logger.warning("【36氪】LLM服务不可用，将跳过向量化")

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._running = False

    async def initialize(self) -> bool:
        """
        初始化采集器（启动Playwright浏览器）

        Returns:
            是否初始化成功
        """
        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )

            self.chroma_storage.create_collection(
                collection_name=self.chroma_collection
            )

            logger.info(f"【36氪】采集器初始化成功: {self.url}")
            return True
        except Exception as e:
            logger.error(f"【36氪】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【36氪】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【36氪】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【36氪】采集失败: {e}")

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        await self._close_browser()
        logger.info("【36氪】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新item_id
        2. Playwright爬取快讯页，提取window.initialState
        3. 过滤已存在item_id
        4. 并发存储到MySQL + ChromaDB
        """
        try:
            latest_item_id = await self._get_latest_stored_item_id()
            logger.debug(f"Latest stored item_id: {latest_item_id}")

            newsflash_list = await self._scrape_news_list(latest_item_id)

            if not newsflash_list:
                logger.debug("No new items to collect")
                return

            new_items = self._filter_new_items(newsflash_list, latest_item_id)

            if new_items:
                await self._store_items(new_items)
                logger.info(f"【36氪】采集到 {len(new_items)} 条新快讯")
            else:
                logger.debug("【36氪】所有消息已存在，无新数据")

        except Exception as e:
            logger.error(f"【36氪】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_item_id(self) -> Optional[str]:
        """
        获取MySQL中最新快讯的item_id（使用ORM）

        Returns:
            最新item_id，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(Kr36Message).filter(
                    Kr36Message.item_id.isnot(None)
                ).order_by(
                    Kr36Message.published_at.desc()
                ).first()

                if latest and latest.item_id:
                    return str(latest.item_id)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest item_id: {e}")
            return None

    async def _scrape_news_list(self, latest_item_id: Optional[str]) -> List[Dict[str, Any]]:
        """
        Playwright爬取快讯页，提取window.initialState数据

        Args:
            latest_item_id: 最新已存储的item_id，遇到此ID立即停止

        Returns:
            快讯列表
        """
        page: Optional[Page] = None
        max_retries = 3
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                page = await self._browser.new_page()

                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                })

                await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(2)
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"【36氪】第 {attempt + 1} 次尝试失败: {e}，{retry_delay}秒后重试...")
                    if page:
                        await page.close()
                        page = None
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【36氪】所有重试均失败: {e}", exc_info=True)
                    if page:
                        await page.close()
                    return []

        if not page:
            return []

        try:

            initial_state_data = await page.evaluate("""
                () => {
                    if (window.initialState &&
                        window.initialState.newsflashCatalogData &&
                        window.initialState.newsflashCatalogData.data &&
                        window.initialState.newsflashCatalogData.data.newsflashList &&
                        window.initialState.newsflashCatalogData.data.newsflashList.data &&
                        window.initialState.newsflashCatalogData.data.newsflashList.data.itemList) {
                        return window.initialState.newsflashCatalogData.data.newsflashList.data.itemList;
                    }
                    return null;
                }
            """)

            if not initial_state_data:
                logger.warning("【36氪】未找到window.initialState数据")
                return []

            newsflash_list = []
            for item_data in initial_state_data:
                item_id = str(item_data.get('itemId', ''))

                # 遇到已存在ID，立即停止
                if latest_item_id and item_id == latest_item_id:
                    logger.debug(f"Reached latest stored item_id ({latest_item_id}), stopping")
                    break

                article = self._extract_article_from_json(item_data, latest_item_id)
                if article:
                    newsflash_list.append(article)

            return newsflash_list

        except Exception as e:
            logger.error(f"Failed to scrape news list: {e}", exc_info=True)
            return []
        finally:
            if page:
                await page.close()

    def _extract_article_from_json(
        self,
        item_data: Dict[str, Any],
        latest_item_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        从JSON数据中提取文章信息

        Args:
            item_data: 快讯item数据
            latest_item_id: 最新已存储的item_id

        Returns:
            文章数据字典
        """
        try:
            item_id = str(item_data.get('itemId', ''))
            if not item_id:
                return None

            template_material = item_data.get('templateMaterial', {})

            title = template_material.get('widgetTitle', '').strip()
            content = template_material.get('widgetContent', '').strip()

            if not title or not content:
                return None

            publish_time_ms = template_material.get('publishTime', 0)
            published_at = datetime.fromtimestamp(publish_time_ms / 1000) if publish_time_ms else datetime.now()

            kr_route = item_data.get('route', '')
            source_url = template_material.get('sourceUrlRoute', '')
            image_url = template_material.get('widgetImage', '')
            comment_count = template_material.get('statComment', 0)
            has_relevant = bool(template_material.get('hasRelevant', 0))

            final_url = None
            if source_url:
                if source_url.startswith('webview?url='):
                    encoded_url = source_url.replace('webview?url=', '')
                    final_url = unquote(encoded_url)
                else:
                    final_url = source_url
            elif kr_route:
                final_url = f"https://www.36kr.com/{kr_route}"

            return {
                "item_id": item_id,
                "title": title,
                "content": content,
                "published_at": published_at,
                "kr_route": kr_route if kr_route else None,
                "source_url": final_url,
                "image_url": image_url if image_url else None,
                "comment_count": comment_count,
                "has_relevant": has_relevant
            }
        except Exception as e:
            logger.error(f"Failed to extract article from JSON: {e}")
            return None

    def _filter_new_items(
        self,
        newsflash_list: List[Dict[str, Any]],
        latest_item_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        过滤已存在的快讯

        Args:
            newsflash_list: 快讯列表
            latest_item_id: 最新已存储item_id

        Returns:
            新快讯列表
        """
        if not latest_item_id:
            return newsflash_list

        new_items = []
        for item in newsflash_list:
            if item.get('item_id') == latest_item_id:
                break
            new_items.append(item)

        return new_items

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        """
        并发存储到MySQL和ChromaDB

        Args:
            items: 快讯列表
        """
        mysql_task = self._store_to_mysql(items)
        chroma_task = self._store_to_chroma(items)
        await asyncio.gather(mysql_task, chroma_task, return_exceptions=True)

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到MySQL

        Args:
            items: 快讯列表
        """
        try:
            with create_session() as db:
                for item in items:
                    summary = self._generate_summary(item['title'], item['content'])

                    message = Kr36Message(
                        id=str(uuid.uuid4()),
                        source_id=self.source_id,
                        item_id=item['item_id'],
                        title=item['title'],
                        content=item['content'],
                        summary=summary,
                        published_at=item.get('published_at'),
                        kr_route=item.get('kr_route'),
                        source_url=item.get('source_url'),
                        image_url=item.get('image_url'),
                        comment_count=item.get('comment_count', 0),
                        has_relevant=item.get('has_relevant', False),
                        crawled_at=datetime.now()
                    )

                    try:
                        db.add(message)
                        db.commit()
                        logger.debug(f"Inserted to MySQL: item_id={item.get('item_id')}")
                    except IntegrityError as e:
                        db.rollback()
                        if "Duplicate entry" in str(e):
                            logger.debug(f"Duplicate item_id: {item['item_id']}")
                        else:
                            logger.error(f"MySQL insert error: {e}")
        except Exception as e:
            logger.error(f"Failed to store to MySQL: {e}")

    async def _store_to_chroma(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到ChromaDB

        Args:
            items: 快讯列表
        """
        try:
            for item in items:
                summary = self._generate_summary(item['title'], item['content'])
                document_text = f"{item['title']} {summary}"

                embedding = self.embedding_client.generate_embedding(document_text)

                self.chroma_storage.upsert(
                    collection_name=self.chroma_collection,
                    ids=[item.get('item_id', str(uuid.uuid4()))],
                    documents=[document_text],
                    metadatas=[{
                        "source_id": self.source_id,
                        "item_id": item.get('item_id', ''),
                        "published_at": item['published_at'].isoformat() if item.get('published_at') else '',
                        "kr_route": item.get('kr_route', ''),
                        "source_url": item.get('source_url', ''),
                        "title": item['title']
                    }],
                    embeddings=[embedding]
                )
                logger.debug(f"Inserted to ChromaDB: item_id={item.get('item_id')}")
        except Exception as e:
            logger.error(f"Failed to store to ChromaDB: {e}")

    def _generate_summary(self, title: str, content: str) -> str:
        """
        生成摘要

        36氪快讯通常较短，直接使用content作为摘要
        如果内容超过1000字，截取前1000字

        Args:
            title: 标题
            content: 内容

        Returns:
            摘要文本
        """
        if len(content) < 1000:
            return content
        return content[:1000] + "..."

    async def _close_browser(self) -> None:
        """关闭浏览器"""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.error(f"Failed to close browser: {e}")
