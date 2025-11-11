# -*- coding: utf-8 -*-

"""
RAND Corporation - Artificial Intelligence Collector
兰德公司人工智能研究采集器
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright
from sqlalchemy.exc import IntegrityError

from backend.database.entities import RANDMessage
from backend.database.connection import create_session
from backend.utils import PageLoader

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

logger = logging.getLogger(__name__)


class RANDCollector:
    """RAND Corporation AI研究采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - url: RAND AI页面URL
                - source_id: 消息源ID（关联message_sources表）
                - region: 地区（US）
                - timezone: 时区（America/Los_Angeles）
                - language: 语言（en）
        """
        self.config = config
        self.interval = config.get('interval', 86400)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.url = config['config'].get('url', 'https://www.rand.org/topics/featured/artificial-intelligence.html')
        self.source_id = config.get('id', 'auto')
        self.region = config['config'].get('region', 'US')
        self.timezone = config['config'].get('timezone', 'America/Los_Angeles')
        self.language = config['config'].get('language', 'en')

        # 判断是否需要翻译
        self.needs_translation = self.language != 'zh' and self.region != 'CN'
        self.translator = None

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【RAND】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            if self.needs_translation:
                self.translator = get_translator()
        else:
            self.embedding_client = None
            logger.warning("【RAND】LLM服务不可用，将跳过向量化")

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
            # RAND网站使用CloudFront WAF，headless=False可以绕过
            self._browser = await self._playwright.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )

            if self.chroma_storage:
                self.chroma_storage.create_collection(
                    collection_name=self.chroma_collection
                )

            logger.info(f"【RAND】采集器初始化成功: {self.url}")
            return True
        except Exception as e:
            logger.error(f"【RAND】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【RAND】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【RAND】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【RAND】采集失败: {e}")

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        await self._close_browser()
        logger.info("【RAND】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新文章URL
        2. 使用Playwright爬取featured AI页面
        3. 过滤已存在URL
        4. 访问详情页获取完整content和author
        5. 并发存储到MySQL + ChromaDB
        """
        try:
            latest_url = await self._get_latest_stored_url()
            logger.debug(f"Latest stored URL: {latest_url}")

            articles_list = await self._scrape_articles_list(latest_url)

            if not articles_list:
                logger.debug("No new items to collect")
                return

            new_items = self._filter_new_items(articles_list, latest_url)

            if new_items:
                # RAND的反爬虫机制过于严格，详情页访问经常失败
                # 简化策略：只使用列表页数据，标题作为content
                logger.info(f"【RAND】采集到 {len(new_items)} 篇新文章（使用列表页数据）")

                # 确保所有项目都有基本的content
                for item in new_items:
                    if not item.get('content'):
                        item['content'] = item['title']
                    # provider从详情页获取，列表页没有，留空
                    if not item.get('provider'):
                        item['provider'] = "RAND Corporation"

                await self._store_items(new_items)
                logger.info(f"【RAND】成功存储 {len(new_items)} 篇文章")
            else:
                logger.debug("【RAND】所有文章已存在，无新数据")

        except Exception as e:
            logger.error(f"【RAND】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新文章的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(RANDMessage).filter(
                    RANDMessage.source_id == self.source_id,
                    RANDMessage.url.isnot(None)
                ).order_by(
                    RANDMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL: {e}")
            return None

    async def _scrape_articles_list(self, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        使用Playwright抓取RAND featured AI页面，提取文章列表

        Args:
            latest_url: 最新已存储的URL，遇到此URL立即停止

        Returns:
            文章列表
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
                    'Accept-Language': 'en-US,en;q=0.9',
                })

                await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"【RAND】第 {attempt + 1} 次尝试失败: {e}，{retry_delay}秒后重试...")
                    if page:
                        await page.close()
                        page = None
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【RAND】所有重试均失败: {e}", exc_info=True)
                    if page:
                        await page.close()
                    return []

        if not page:
            return []

        try:
            # 等待文章列表加载
            await page.wait_for_selector('ul.teasers li[data-content-id]', timeout=15000)

            # 全量加载：滚动/点击加载更多
            item_selector = 'ul.teasers li[data-content-id]'
            final_count = await PageLoader.load_all_content(
                page=page,
                item_selector=item_selector,
                max_scrolls=30,
                scroll_delay=3.0,
                load_more_selectors=[
                    'button:has-text("Load More")',
                    'button:has-text("Show More")',
                    'a.load-more',
                    '[class*="load-more"]'
                ]
            )
            logger.info(f"【RAND】全量加载完成，共 {final_count} 篇文章")

            # 提取文章列表
            article_elements = await page.query_selector_all('ul.teasers li[data-content-id]')
            logger.debug(f"Found {len(article_elements)} article elements")

            articles_list = []
            for article_elem in article_elements:
                article_data = await self._extract_article_from_element(article_elem)

                if not article_data:
                    continue

                article_url = article_data.get('url')
                if not article_url:
                    continue

                # 检查是否达到最新已存储URL
                if latest_url and article_url == latest_url:
                    logger.debug(f"Reached latest stored URL ({latest_url}), stopping")
                    break

                articles_list.append(article_data)

            return articles_list

        except Exception as e:
            logger.error(f"Failed to scrape articles list: {e}", exc_info=True)
            return []
        finally:
            if page:
                await page.close()

    async def _fetch_article_detail(self, article_url: str) -> Optional[Dict[str, Any]]:
        """
        访问文章详情页，获取完整author和content

        Args:
            article_url: 文章URL

        Returns:
            包含author, content, summary的字典
        """
        detail_page: Optional[Page] = None
        try:
            detail_page = await self._browser.new_page()

            await detail_page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            })

            await detail_page.goto(article_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            result = {}

            # 提取作者
            author_elem = await detail_page.query_selector('.author, .authors, [class*="author"]')
            if author_elem:
                author_text = await author_elem.inner_text()
                result['provider'] = author_text.strip()

            # 提取摘要
            summary_elem = await detail_page.query_selector('.abstract, .summary, [class*="abstract"]')
            if summary_elem:
                summary_text = await summary_elem.inner_text()
                result['summary'] = summary_text.strip()

            # 提取正文
            paragraphs = await detail_page.query_selector_all('.product-main p, article p, .content p, .product-body p')
            content_parts = []

            for para in paragraphs:
                para_text = (await para.inner_text()).strip()
                # 过滤掉非正文内容
                if para_text and len(para_text) > 20:
                    # 排除分享按钮、订阅提示等
                    if not any(keyword in para_text.lower() for keyword in ['share', 'follow us', 'subscribe', 'newsletter', 'download']):
                        content_parts.append(para_text)

            if content_parts:
                result['content'] = '\n\n'.join(content_parts)

            return result if result else None

        except Exception as e:
            logger.error(f"获取文章详情失败 {article_url}: {e}")
            return None
        finally:
            if detail_page:
                await detail_page.close()

    async def _extract_article_from_element(self, article_elem) -> Optional[Dict[str, Any]]:
        """
        从li[data-content-id]元素中提取文章数据

        Args:
            article_elem: li[data-content-id] DOM元素

        Returns:
            文章数据字典
        """
        try:
            # 提取content-id
            content_id = await article_elem.get_attribute('data-content-id')

            # 提取标题
            title_elem = await article_elem.query_selector('h3.title, h2, h3')
            if not title_elem:
                return None
            title = (await title_elem.inner_text()).strip()

            # 提取链接
            link_elem = await article_elem.query_selector('a[href]')
            if not link_elem:
                return None
            url = await link_elem.get_attribute('href')

            if not url:
                return None

            # 补全相对URL
            if url.startswith('/'):
                url = f"https://www.rand.org{url}"

            # 提取类型
            type_elem = await article_elem.query_selector('.type')
            category = ""
            if type_elem:
                category = (await type_elem.inner_text()).strip().upper()

            # 提取日期
            date_elem = await article_elem.query_selector('p.date, .date')
            published_at = None
            if date_elem:
                date_text = (await date_elem.inner_text()).strip()
                published_at = self._parse_date_text(date_text)

            if not published_at:
                published_at = datetime.now()

            # external_id就是content_id
            external_id = content_id

            return {
                "external_id": external_id,
                "title": title,
                "content": title,  # 暂用title，详情页会覆盖
                "summary": None,  # 详情页会补充
                "provider": None,  # 详情页会补充
                "published_at": published_at,
                "url": url,
                "region": self.region,
                "category": category if category else "RESEARCH",
                "language": self.language
            }
        except Exception as e:
            logger.error(f"Failed to extract article from element: {e}")
            return None

    def _parse_date_text(self, date_text: str) -> datetime:
        """
        解析日期文本

        Args:
            date_text: 日期文本，如 "Sep 30, 2025"

        Returns:
            datetime对象
        """
        if not date_text:
            return datetime.now()

        try:
            # 尝试解析RAND格式：Sep 30, 2025
            return datetime.strptime(date_text.strip(), '%b %d, %Y')
        except Exception:
            pass

        try:
            # 尝试其他常见格式
            for fmt in ['%B %d, %Y', '%Y-%m-%d', '%m/%d/%Y']:
                try:
                    return datetime.strptime(date_text.strip(), fmt)
                except ValueError:
                    continue
            return datetime.now()
        except Exception as e:
            logger.error(f"Failed to parse date text '{date_text}': {e}")
            return datetime.now()

    def _filter_new_items(
        self,
        articles_list: List[Dict[str, Any]],
        latest_url: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        过滤已存在的文章

        Args:
            articles_list: 文章列表
            latest_url: 最新已存储URL

        Returns:
            新文章列表
        """
        if not latest_url:
            return articles_list

        new_items = []
        for item in articles_list:
            if item.get('url') == latest_url:
                break
            new_items.append(item)

        return new_items

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        """
        并发存储到MySQL和ChromaDB

        Args:
            items: 文章列表
        """
        mysql_task = self._store_to_mysql(items)
        chroma_task = self._store_to_chroma(items)
        await asyncio.gather(mysql_task, chroma_task, return_exceptions=True)

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到MySQL

        Args:
            items: 文章列表
        """
        try:
            # 步骤1：预先翻译所有summary（在session外，避免长时间占用连接）
            summaries = {}
            for item in items:
                summaries[item['url']] = await self._generate_summary(
                    item.get('summary'),
                    item.get('content', '')
                )

            # 步骤2：批量入库（在session内）
            with create_session() as db:
                for item in items:
                    message = RANDMessage(
                        id=str(uuid.uuid4()),
                        source_id=self.source_id,
                        external_id=item.get('external_id'),
                        title=item['title'],
                        content=item['content'],
                        summary=summaries[item['url']],
                        provider=item.get('provider'),
                        published_at=item.get('published_at'),
                        crawled_at=datetime.now(),
                        url=item['url'],
                        region=item.get('region'),
                        category=item.get('category'),
                        language=item.get('language')
                    )

                    try:
                        db.add(message)
                        db.commit()
                        logger.debug(f"Inserted to MySQL: url={item.get('url')}")
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
            items: 文章列表
        """
        if not self.chroma_storage or not self.embedding_client:
            return

        try:
            for item in items:
                summary = await self._generate_summary(item.get('summary'), item.get('content', ''))
                document_text = f"{item['title']} {summary}"

                embedding = self.embedding_client.generate_embedding(document_text)

                chroma_id = item.get('url') or str(uuid.uuid4())

                self.chroma_storage.upsert(
                    collection_name=self.chroma_collection,
                    ids=[chroma_id],
                    documents=[document_text],
                    metadatas=[{
                        "source_id": self.source_id,
                        "external_id": item.get('external_id', ''),
                        "published_at": item['published_at'].isoformat() if item.get('published_at') else '',
                        "url": item.get('url', ''),
                        "title": item['title'],
                        "provider": item.get('provider', ''),
                        "region": item.get('region', ''),
                        "category": item.get('category', ''),
                        "language": item.get('language', '')
                    }],
                    embeddings=[embedding]
                )
                logger.debug(f"Inserted to ChromaDB: url={item.get('url')}")
        except Exception as e:
            logger.error(f"Failed to store to ChromaDB: {e}")

    async def _generate_summary(self, summary: Optional[str], content: str) -> str:
        """
        生成摘要（支持翻译）

        完整决策流程：
        1. 确定原始摘要来源（优先summary，无则用content）
        2. 判断是否需要翻译（外文消息源）
        3. 中文：根据长度决定是否截断
        4. 外文：调用translator.translate()进行翻译

        Args:
            summary: 网页提取的摘要
            content: 正文内容

        Returns:
            摘要文本（中文消息源为原文，外文消息源为中文翻译）
        """
        # 确定原始文本
        source_text = summary.strip() if summary and len(summary.strip()) > 0 else content

        # 中文消息源：直接返回或截断
        if not self.needs_translation:
            if len(source_text) <= 1000:
                return source_text
            return source_text[:1000] + "..."

        # 外文消息源：翻译为中文（全文翻译，不限制长度）
        if self.translator:
            try:
                translated = await self.translator.translate(
                    text=source_text,
                    context="RAND智库研究报告摘要"
                )
                return translated
            except Exception as e:
                logger.error(f"翻译失败: {e}")
                # 翻译失败降级：返回截断原文
                return source_text[:500] + "... [AI翻译暂不可用]"

        # 无translator可用：返回截断原文
        if len(source_text) <= 1000:
            return source_text
        return source_text[:1000] + "..."

    async def _close_browser(self) -> None:
        """关闭浏览器"""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.error(f"Failed to close browser: {e}")
