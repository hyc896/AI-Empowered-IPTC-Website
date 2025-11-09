# -*- coding: utf-8 -*-

"""
TongHuaShun Collector
同花顺独立采集器，参考 D:/TechWork/tonghuashun/scrape_news.py
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright
from sqlalchemy.exc import IntegrityError

from backend.database.entities import TongHuaShunMessage
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


class TongHuaShunCollector:
    """同花顺独立采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - url: 同花顺快讯URL
                - source_id: 消息源ID（关联message_sources表）
        """
        self.config = config
        self.interval = config.get('interval', 15)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.url = config['config'].get('url', 'https://news.10jqka.com.cn/realtimenews.html')
        self.source_id = config.get('id', 'auto')

        # 优雅地处理缺失的依赖
        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【同花顺】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
        else:
            self.embedding_client = None
            logger.warning("【同花顺】LLM服务不可用，将跳过向量化")

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
            self._browser = await self._playwright.chromium.launch(headless=True)

            self.chroma_storage.create_collection(
                collection_name=self.chroma_collection
            )

            logger.info(f"【同花顺】采集器初始化成功: {self.url}")
            return True
        except Exception as e:
            logger.error(f"【同花顺】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【同花顺】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【同花顺】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【同花顺】采集失败: {e}")

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        await self._close_browser()
        logger.info("【同花顺】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新新闻ID
        2. Playwright爬取列表页
        3. 过滤已存在ID（URL提取ID去重）
        4. 并发存储到MySQL + ChromaDB
        """
        try:
            latest_id = await self._get_latest_stored_id()
            logger.debug(f"Latest stored ID: {latest_id}")

            news_list = await self._scrape_news_list(latest_id)

            if not news_list:
                logger.debug("No new items to collect")
                return

            new_items = self._filter_new_items(news_list, latest_id)

            if new_items:
                await self._store_items(new_items)
                logger.info(f"【同花顺】采集到 {len(new_items)} 条新快讯")
            else:
                logger.debug("【同花顺】所有消息已存在，无新数据")

        except Exception as e:
            logger.error(f"【同花顺】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_id(self) -> Optional[str]:
        """
        获取MySQL中最新新闻的ID（使用ORM）

        Returns:
            最新新闻ID，如果没有返回None
        """
        try:
            with create_session() as db:
                # 修复：按抓取时间降序，而不是发布时间（避免日期解析错误导致的排序不稳定）
                latest = db.query(TongHuaShunMessage).filter(
                    TongHuaShunMessage.seq.isnot(None)
                ).order_by(
                    TongHuaShunMessage.crawled_at.desc()
                ).first()

                if latest and latest.seq:
                    logger.debug(f"Latest stored: seq={latest.seq}, crawled_at={latest.crawled_at}, published_at={latest.published_at}")
                    return str(latest.seq)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest ID: {e}")
            return None

    async def _scrape_news_list(self, latest_id: Optional[str]) -> List[Dict[str, Any]]:
        """
        Playwright爬取列表页

        Args:
            latest_id: 最新已存储的ID，遇到此ID立即停止

        Returns:
            新闻列表
        """
        page: Optional[Page] = None
        try:
            page = await self._browser.new_page()
            await page.goto(self.url, wait_until="domcontentloaded", timeout=30000)

            news_list_selector = "ul.newsText.all"
            await page.wait_for_selector(news_list_selector, timeout=15000)

            # 修复：获取所有li元素（包括日期标记li和新闻li）
            all_items = await page.query_selector_all(f"{news_list_selector} > li")

            news_list = []
            current_date = date.today().strftime('%Y-%m-%d')  # 默认今天

            for item in all_items:
                # 检查是否是日期标记li
                class_name = await item.get_attribute("class")
                if class_name and "beforeNewTime" in class_name:
                    # 这是日期标记，更新current_date
                    date_text = await item.inner_text()
                    try:
                        date_obj = datetime.strptime(date_text.strip(), '%Y.%m.%d')
                        current_date = date_obj.strftime('%Y-%m-%d')
                        logger.debug(f"Date marker found: {current_date}")
                    except ValueError:
                        logger.warning(f"Cannot parse date marker: {date_text}")
                    continue

                # 这是新闻li，提取数据
                detail_link = await item.query_selector("div.newsDetail > a")
                if not detail_link:
                    continue

                href = await detail_link.get_attribute("href")
                if not href:
                    continue

                news_id = self._extract_id_from_url(href)
                if not news_id:
                    continue

                if latest_id and news_id == latest_id:
                    logger.debug(f"Reached latest stored ID ({latest_id}), stopping")
                    break

                # 传入current_date而不是让函数自己查找
                article_data = await self._extract_article_from_element(item, detail_link, href, news_id, current_date)
                if article_data:
                    news_list.append(article_data)

            return news_list

        except Exception as e:
            logger.error(f"Failed to scrape news list: {e}")
            return []
        finally:
            if page:
                await page.close()

    async def _extract_article_from_element(
        self,
        li_element,
        link_element,
        url: str,
        seq: str,
        current_date: str
    ) -> Optional[Dict[str, Any]]:
        """
        从li元素中提取文章数据

        Args:
            li_element: li DOM元素
            link_element: a链接元素
            url: 文章URL
            seq: 序列号
            current_date: 当前日期（YYYY-MM-DD格式）

        Returns:
            文章数据字典
        """
        try:
            title_element = await link_element.query_selector("strong")
            title = await title_element.inner_text() if title_element else ""

            full_text = await link_element.inner_text() if link_element else ""
            content_with_source = full_text.replace(title, "", 1).strip()

            source_match = re.search(r'[（(](.*?)[）)]$', content_with_source)
            provider = ""
            content = content_with_source
            if source_match:
                candidate_provider = source_match.group(1)
                match_position = source_match.start()
                distance_from_end = len(content_with_source) - match_position

                if distance_from_end <= 20 and len(candidate_provider) <= 10:
                    provider = candidate_provider
                    content = content_with_source[:match_position].strip()
                else:
                    content = content_with_source

            time_element = await li_element.query_selector(".newsTimer")
            time_text = await time_element.inner_text() if time_element else ""
            # 修复：使用传入的current_date，而不是自己查找
            published_at = self._parse_datetime_simple(current_date, time_text)

            image_url = None
            img_element = await link_element.query_selector("img")
            if img_element:
                image_url = await img_element.get_attribute("src")

            return {
                "title": title.strip(),
                "content": content.strip(),
                "provider": provider.strip() if provider else None,
                "published_at": published_at,
                "url": url,
                "image_url": image_url,
                "seq": seq
            }
        except Exception as e:
            logger.error(f"Failed to extract article: {e}")
            return None

    def _parse_datetime_simple(self, current_date: str, time_text: str) -> datetime:
        """
        解析日期时间（简化版，使用传入的日期）

        Args:
            current_date: 当前日期（YYYY-MM-DD格式）
            time_text: 时间文本，如 "14:30"

        Returns:
            datetime对象
        """
        try:
            datetime_str = f"{current_date} {time_text.strip()}"
            return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        except Exception as e:
            logger.error(f"Failed to parse datetime: {e}")
            return datetime.now()

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取ID

        Args:
            url: 文章URL，如 /c123456.shtml

        Returns:
            ID字符串，如 "123456"
        """
        match = re.search(r'/c(\d+)\.shtml', url)
        return match.group(1) if match else None

    def _filter_new_items(
        self,
        news_list: List[Dict[str, Any]],
        latest_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        过滤已存在的新闻

        Args:
            news_list: 新闻列表
            latest_id: 最新已存储ID

        Returns:
            新新闻列表
        """
        if not latest_id:
            return news_list

        new_items = []
        for item in news_list:
            if item.get('seq') == latest_id:
                break
            new_items.append(item)

        return new_items

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        """
        并发存储到MySQL和ChromaDB

        Args:
            items: 新闻列表
        """
        mysql_task = self._store_to_mysql(items)
        chroma_task = self._store_to_chroma(items)
        await asyncio.gather(mysql_task, chroma_task, return_exceptions=True)

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到MySQL

        Args:
            items: 新闻列表
        """
        try:
            with create_session() as db:
                for item in items:
                    summary = self._generate_summary(item['title'], item['content'])

                    message = TongHuaShunMessage(
                        id=str(uuid.uuid4()),
                        source_id=self.source_id,
                        title=item['title'],
                        content=item['content'],
                        summary=summary,
                        provider=item.get('provider'),
                        published_at=item.get('published_at'),
                        url=item['url'],
                        image_url=item.get('image_url'),
                        seq=item.get('seq'),
                        tags=[],
                        crawled_at=datetime.now()
                    )

                    try:
                        db.add(message)
                        db.commit()
                        logger.debug(f"Inserted to MySQL: seq={item.get('seq')}")
                    except IntegrityError as e:
                        db.rollback()
                        if "Duplicate entry" in str(e):
                            logger.debug(f"Duplicate URL: {item['url']}")
                        else:
                            logger.error(f"MySQL insert error: {e}")
        except Exception as e:
            logger.error(f"Failed to store to MySQL: {e}")

    async def _store_to_chroma(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到ChromaDB

        Args:
            items: 新闻列表
        """
        try:
            for item in items:
                summary = self._generate_summary(item['title'], item['content'])
                document_text = f"{item['title']} {summary}"

                embedding = self.embedding_client.generate_embedding(document_text)

                chroma_id = item.get('seq') or item.get('url') or str(uuid.uuid4())

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
                logger.debug(f"Inserted to ChromaDB: seq={item.get('seq')}, chroma_id={chroma_id}")
        except Exception as e:
            logger.error(f"Failed to store to ChromaDB: {e}")

    def _generate_summary(self, title: str, content: str) -> str:
        """
        生成摘要

        同花顺快讯通常较短，直接使用content作为摘要
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
