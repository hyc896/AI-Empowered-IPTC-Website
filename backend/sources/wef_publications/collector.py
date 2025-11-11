# -*- coding: utf-8 -*-

"""
World Economic Forum (WEF) AI Publications Collector
世界经济论坛AI出版物采集器
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright
from sqlalchemy.exc import IntegrityError

from backend.database.entities import WEFPublicationMessage
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

try:
    from backend.llm import get_translator
    _translator_available = True
except ImportError:
    _translator_available = False

logger = logging.getLogger(__name__)


class WEFPublicationsCollector:
    """World Economic Forum AI Publications采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - url: WEF Publications URL
                - source_id: 消息源ID（关联message_sources表）
                - region: 地区（GLOBAL）
                - timezone: 时区（Europe/Zurich）
                - language: 语言（en）
        """
        self.config = config
        self.interval = config.get('interval', 86400)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.url = config['config'].get('url', 'https://www.weforum.org/publications/')
        self.source_id = config.get('id', 'auto')
        self.region = config['config'].get('region', 'GLOBAL')
        self.timezone = config['config'].get('timezone', 'Europe/Zurich')
        self.language = config['config'].get('language', 'en')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【WEF Publications】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
        else:
            self.embedding_client = None
            logger.warning("【WEF Publications】LLM服务不可用，将跳过向量化")

        if _translator_available and self.language == 'en':
            self.translator = get_translator()
            self.needs_translation = True
        else:
            self.translator = None
            self.needs_translation = False

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

            if self.chroma_storage:
                self.chroma_storage.create_collection(
                    collection_name=self.chroma_collection
                )

            logger.info(f"【WEF Publications】采集器初始化成功: {self.url}")
            return True
        except Exception as e:
            logger.error(f"【WEF Publications】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【WEF Publications】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【WEF Publications】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【WEF Publications】采集失败: {e}")

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        await self._close_browser()
        logger.info("【WEF Publications】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新出版物URL
        2. Playwright爬取列表页
        3. 过滤已存在URL
        4. 访问详情页获取完整content
        5. 并发存储到MySQL + ChromaDB
        """
        try:
            latest_url = await self._get_latest_stored_url()
            logger.debug(f"Latest stored URL: {latest_url}")

            publications_list = await self._scrape_publications_list(latest_url)

            if not publications_list:
                logger.debug("No new items to collect")
                return

            new_items = self._filter_new_items(publications_list, latest_url)

            if new_items:
                # 访问详情页获取完整content
                logger.info(f"【WEF Publications】开始访问 {len(new_items)} 篇出版物的详情页...")
                for idx, item in enumerate(new_items, 1):
                    try:
                        full_content = await self._fetch_publication_content(item['url'])
                        if full_content:
                            item['content'] = full_content['content']
                            item['summary'] = full_content.get('summary', '')
                            item['provider'] = full_content.get('provider')
                            logger.debug(f"[{idx}/{len(new_items)}] ✓ 获取完整内容: {item['url']}")
                        else:
                            logger.debug(f"[{idx}/{len(new_items)}] ⚠ 保持使用标题: {item['url']}")
                    except Exception as e:
                        logger.error(f"[{idx}/{len(new_items)}] ✗ 详情页访问失败: {e}")

                    # 添加延迟，避免请求过快
                    await asyncio.sleep(2)

                await self._store_items(new_items)
                logger.info(f"【WEF Publications】采集到 {len(new_items)} 篇新出版物")
            else:
                logger.debug("【WEF Publications】所有出版物已存在，无新数据")

        except Exception as e:
            logger.error(f"【WEF Publications】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新出版物的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(WEFPublicationMessage).filter(
                    WEFPublicationMessage.source_id == self.source_id,
                    WEFPublicationMessage.url.isnot(None)
                ).order_by(
                    WEFPublicationMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL: {e}")
            return None

    async def _scrape_publications_list(self, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        Playwright爬取列表页，提取出版物列表

        Args:
            latest_url: 最新已存储的URL，遇到此URL立即停止

        Returns:
            出版物列表
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
                await asyncio.sleep(5)
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"【WEF Publications】第 {attempt + 1} 次尝试失败: {e}，{retry_delay}秒后重试...")
                    if page:
                        await page.close()
                        page = None
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【WEF Publications】所有重试均失败: {e}", exc_info=True)
                    if page:
                        await page.close()
                    return []

        if not page:
            return []

        try:
            # 滚动到"All publications"区域
            await page.evaluate("window.scrollTo(0, 1600)")
            await asyncio.sleep(3)

            # 等待出版物卡片加载（WEF使用article标签）
            publications_selector = "article"
            await page.wait_for_selector(publications_selector, timeout=15000)

            # 获取所有出版物卡片
            publication_elements = await page.query_selector_all(publications_selector)
            logger.debug(f"Found {len(publication_elements)} publication elements")

            publications_list = []
            for pub_elem in publication_elements:
                pub_data = await self._extract_publication_from_element(pub_elem)

                if not pub_data:
                    continue

                pub_url = pub_data.get('url')
                if not pub_url:
                    continue

                # 只收集AI相关的出版物（通过标题关键词过滤）
                title = pub_data.get('title', '').lower()
                if not any(keyword in title for keyword in ['artificial intelligence', 'ai ', ' ai', 'machine learning', 'intelligent']):
                    continue

                if latest_url and pub_url == latest_url:
                    logger.debug(f"Reached latest stored URL ({latest_url}), stopping")
                    break

                publications_list.append(pub_data)

            return publications_list

        except Exception as e:
            logger.error(f"Failed to scrape publications list: {e}", exc_info=True)
            return []
        finally:
            if page:
                await page.close()

    async def _fetch_publication_content(self, publication_url: str) -> Optional[Dict[str, Any]]:
        """
        访问出版物详情页，获取完整内容

        Args:
            publication_url: 出版物URL

        Returns:
            包含content, summary, provider的字典
        """
        detail_page: Optional[Page] = None
        try:
            detail_page = await self._browser.new_page()

            await detail_page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            })

            await detail_page.goto(publication_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # 提取摘要（第一段描述性文字）
            summary_elem = await detail_page.query_selector('p')
            summary = (await summary_elem.inner_text()).strip() if summary_elem else ''

            # 提取完整正文内容
            paragraphs = await detail_page.query_selector_all('main p, article p, [class*="content"] p')
            content_parts = []

            for para in paragraphs:
                para_text = (await para.inner_text()).strip()
                # 过滤掉非正文内容
                if para_text and len(para_text) > 50:
                    # 排除短的元信息
                    if not (len(para_text) < 100 and any(keyword in para_text for keyword in ['Published:', 'Download', 'Sign up', 'collaboration with'])):
                        content_parts.append(para_text)

            full_content = '\n\n'.join(content_parts)

            # 提取合作方信息
            provider = None
            provider_elem = await detail_page.query_selector('[class*="collaboration"]')
            if provider_elem:
                provider_text = (await provider_elem.inner_text()).strip()
                # 提取"In collaboration with XXX"中的组织名称
                match = re.search(r'In collaboration with (.+)', provider_text)
                if match:
                    provider = match.group(1).strip()

            return {
                'content': full_content if full_content else summary,
                'summary': summary,
                'provider': provider
            }

        except Exception as e:
            logger.error(f"获取出版物详情失败 {publication_url}: {e}")
            return None
        finally:
            if detail_page:
                await detail_page.close()

    async def _extract_publication_from_element(self, pub_elem) -> Optional[Dict[str, Any]]:
        """
        从出版物卡片元素中提取数据

        Args:
            pub_elem: 出版物卡片DOM元素

        Returns:
            出版物数据字典
        """
        try:
            # 提取标题
            title_elem = await pub_elem.query_selector('h1, h2, h3, h4, [class*="title"]')
            if not title_elem:
                return None

            title = (await title_elem.inner_text()).strip()
            if not title:
                return None

            # 提取URL
            link_elem = await pub_elem.query_selector('a[href*="/publications/"]')
            if not link_elem:
                return None

            url = await link_elem.get_attribute('href')
            if not url:
                return None

            # 确保URL是完整的
            if not url.startswith('http'):
                url = f"https://www.weforum.org{url}"

            # 提取分类
            category_elem = await pub_elem.query_selector('[class*="category"], [class*="label"]')
            category = (await category_elem.inner_text()).strip() if category_elem else None

            # 提取日期
            date_text = None
            date_elem = await pub_elem.query_selector('time, [class*="date"]')
            if date_elem:
                date_text = (await date_elem.inner_text()).strip()

            # 如果没找到，尝试从文本中提取日期
            if not date_text:
                all_text = (await pub_elem.inner_text()).strip()
                date_match = re.search(r'(Oct|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep)\s+\d{1,2},\s+\d{4}', all_text)
                if date_match:
                    date_text = date_match.group(0)

            published_at = self._parse_date_text(date_text) if date_text else datetime.now()

            external_id = self._extract_id_from_url(url)

            return {
                "external_id": external_id,
                "title": title,
                "content": title,  # 暂时使用标题，后续从详情页获取
                "summary": None,
                "provider": None,
                "published_at": published_at,
                "url": url,
                "region": self.region,
                "category": category,
                "language": self.language
            }
        except Exception as e:
            logger.error(f"Failed to extract publication from element: {e}")
            return None

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取出版物ID

        Args:
            url: 出版物URL，如 https://www.weforum.org/publications/artificial-intelligence-for-efficiency/

        Returns:
            出版物路径slug作为ID
        """
        try:
            match = re.search(r'/publications/([^/\?]+)', url)
            return match.group(1) if match else None
        except Exception:
            return None

    def _parse_date_text(self, date_text: str) -> datetime:
        """
        解析日期文本

        Args:
            date_text: 日期文本，如 "Jan 14, 2025" 或 "14 January 2025"

        Returns:
            datetime对象
        """
        try:
            date_text = date_text.strip()
            # 去掉特殊字符
            date_text = date_text.replace('—', '').strip()

            # 尝试多种日期格式
            formats = [
                '%b %d, %Y',      # Jan 14, 2025
                '%B %d, %Y',      # January 14, 2025
                '%d %B %Y',       # 14 January 2025
                '%d %b %Y',       # 14 Jan 2025
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(date_text, fmt)
                except ValueError:
                    continue

            logger.warning(f"无法解析日期格式: {date_text}")
            return datetime.now()
        except Exception as e:
            logger.error(f"Failed to parse date text '{date_text}': {e}")
            return datetime.now()

    def _filter_new_items(
        self,
        publications_list: List[Dict[str, Any]],
        latest_url: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        过滤已存在的出版物

        Args:
            publications_list: 出版物列表
            latest_url: 最新已存储URL

        Returns:
            新出版物列表
        """
        if not latest_url:
            return publications_list

        new_items = []
        for item in publications_list:
            if item.get('url') == latest_url:
                break
            new_items.append(item)

        return new_items

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        """
        并发存储到MySQL和ChromaDB

        Args:
            items: 出版物列表
        """
        mysql_task = self._store_to_mysql(items)
        chroma_task = self._store_to_chroma(items)
        await asyncio.gather(mysql_task, chroma_task, return_exceptions=True)

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到MySQL

        Args:
            items: 出版物列表
        """
        try:
            with create_session() as db:
                for item in items:
                    summary = await self._generate_summary(item.get('summary'), item.get('content', ''))

                    message = WEFPublicationMessage(
                        id=str(uuid.uuid4()),
                        source_id=self.source_id,
                        external_id=item.get('external_id'),
                        title=item['title'],
                        content=item['content'],
                        summary=summary,
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
            items: 出版物列表
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
        生成摘要

        对于外文消息源：
        1. 优先使用网页摘要，翻译成中文
        2. 如无摘要，使用content，翻译前1000字
        3. 翻译失败时降级为截断原文

        Args:
            summary: 网页提取的摘要
            content: 正文内容

        Returns:
            摘要文本（中文）
        """
        # 确定原始摘要来源
        source_text = summary if summary and len(summary.strip()) > 0 else content

        # 中文内容直接返回
        if not self.needs_translation or not self.translator:
            if len(source_text) <= 1000:
                return source_text
            return source_text[:1000] + "..."

        # 外文内容翻译
        try:
            # 限制翻译长度
            text_to_translate = source_text if len(source_text) <= 1000 else source_text[:1000]

            translated = await self.translator.translate(
                text=text_to_translate,
                context="世界经济论坛AI出版物摘要"
            )

            return translated

        except Exception as e:
            logger.error(f"翻译失败: {e}")
            # 降级：返回截断的原文
            if len(source_text) <= 500:
                return f"[AI翻译暂不可用] {source_text}"
            return f"[AI翻译暂不可用] {source_text[:500]}..."

    async def _close_browser(self) -> None:
        """关闭浏览器"""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.error(f"Failed to close browser: {e}")
