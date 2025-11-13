# -*- coding: utf-8 -*-

"""
The Future Society Collector
跨大西洋AI治理智库（美国+比利时）采集器
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright
from sqlalchemy.exc import IntegrityError

from backend.database.entities import FutureSocietyMessage
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

logger = logging.getLogger(__name__)


class FutureSocietyCollector:
    """The Future Society AI治理研究采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - url: The Future Society资源页URL
                - source_id: 消息源ID（关联message_sources表）
                - region: 地区（GLOBAL）
                - language: 语言（en）
        """
        self.config = config
        self.interval = config.get('interval', 86400)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.url = config['config'].get('url', 'https://thefuturesociety.org/resources/')
        self.source_id = config.get('id', 'auto')
        self.region = config['config'].get('region', 'GLOBAL')
        self.language = config['config'].get('language', 'en')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【Future Society】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【Future Society】LLM服务不可用，将跳过向量化和翻译")

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

            logger.info(f"【Future Society】采集器初始化成功: {self.url}")
            return True
        except Exception as e:
            logger.error(f"【Future Society】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【Future Society】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【Future Society】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【Future Society】采集失败: {e}")

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        await self._close_browser()
        logger.info("【Future Society】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新文章URL
        2. Playwright爬取资源页
        3. 过滤已存在URL
        4. 访问详情页获取完整内容
        5. 预翻译summary（在数据库会话外）
        6. 存储到MySQL + ChromaDB
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
                # 访问详情页获取完整content
                logger.info(f"【Future Society】开始访问 {len(new_items)} 篇文章的详情页...")
                for idx, item in enumerate(new_items, 1):
                    try:
                        full_content = await self._fetch_article_content(item['url'])
                        if full_content:
                            item['content'] = full_content
                            logger.debug(f"[{idx}/{len(new_items)}] ✓ 获取完整内容: {item['url']}")
                        else:
                            logger.debug(f"[{idx}/{len(new_items)}] ⚠ 保持使用摘要: {item['url']}")

                        # 延迟避免过快请求
                        await asyncio.sleep(1.5)
                    except Exception as e:
                        logger.error(f"[{idx}/{len(new_items)}] ✗ 详情页访问失败: {e}")

                # 预翻译所有summary（在数据库会话外）
                logger.info(f"【Future Society】开始翻译 {len(new_items)} 篇文章的摘要...")
                for idx, item in enumerate(new_items, 1):
                    try:
                        summary = await self._generate_summary(
                            item.get('summary'),
                            item.get('content', '')
                        )
                        item['translated_summary'] = summary
                        logger.debug(f"[{idx}/{len(new_items)}] ✓ 翻译完成")
                    except Exception as e:
                        logger.error(f"[{idx}/{len(new_items)}] ✗ 翻译失败: {e}")
                        item['translated_summary'] = item.get('content', '')[:500] + "... [AI翻译暂不可用]"

                await self._store_items(new_items)
                logger.info(f"【Future Society】采集到 {len(new_items)} 篇新文章")
            else:
                logger.debug("【Future Society】所有文章已存在，无新数据")

        except Exception as e:
            logger.error(f"【Future Society】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新文章的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(FutureSocietyMessage).filter(
                    FutureSocietyMessage.source_id == self.source_id,
                    FutureSocietyMessage.url.isnot(None)
                ).order_by(
                    FutureSocietyMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL: {e}")
            return None

    async def _scrape_articles_list(self, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        Playwright爬取资源页，提取文章列表

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
                await asyncio.sleep(5)
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"【Future Society】第 {attempt + 1} 次尝试失败: {e}，{retry_delay}秒后重试...")
                    if page:
                        await page.close()
                        page = None
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【Future Society】所有重试均失败: {e}", exc_info=True)
                    if page:
                        await page.close()
                    return []

        if not page:
            return []

        try:
            # 探测页面加载机制
            # 1. 检查是否有"Load More"按钮
            load_more_button = await page.query_selector("button:has-text('Load More'), button:has-text('Show More'), a:has-text('Load More')")

            # 2. 检查是否有分页链接
            pagination_links = await page.query_selector_all("a.pagination-link, .pagination a, nav a[rel='next']")

            # 3. 尝试找到文章列表容器
            # WordPress站点常用选择器：article, .post, .entry, .resource-item
            article_selector = "article, .post, .entry, .resource-wrapper, .resource-item, .publication-item"
            await page.wait_for_selector(article_selector, timeout=15000)

            articles_list = []
            page_num = 1
            max_pages = 10

            while page_num <= max_pages:
                # 提取当前页面的文章
                article_elements = await page.query_selector_all(article_selector)
                logger.debug(f"Page {page_num}: Found {len(article_elements)} articles")

                for article_elem in article_elements:
                    article_data = await self._extract_article_from_element(article_elem)

                    if not article_data:
                        continue

                    article_url = article_data.get('url')
                    if not article_url:
                        continue

                    # 遇到已存在URL立即停止
                    if latest_url and article_url == latest_url:
                        logger.debug(f"Reached latest stored URL ({latest_url}), stopping")
                        return articles_list

                    articles_list.append(article_data)

                # 尝试加载更多
                loaded_more = False

                # 优先尝试点击"Load More"按钮
                if load_more_button:
                    try:
                        await load_more_button.click()
                        await asyncio.sleep(3)
                        loaded_more = True
                        logger.debug(f"Clicked 'Load More' button")
                    except Exception as e:
                        logger.debug(f"Failed to click 'Load More' button: {e}")

                # 如果没有按钮，尝试滚动加载
                if not loaded_more:
                    try:
                        previous_height = await page.evaluate("document.body.scrollHeight")
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(3)
                        new_height = await page.evaluate("document.body.scrollHeight")

                        if new_height > previous_height:
                            loaded_more = True
                            logger.debug("Loaded more content by scrolling")
                    except Exception as e:
                        logger.debug(f"Scrolling failed: {e}")

                # 如果滚动也没用，尝试分页链接
                if not loaded_more and pagination_links:
                    try:
                        next_link = None
                        for link in pagination_links:
                            text = await link.inner_text()
                            if 'next' in text.lower() or '>' in text:
                                next_link = link
                                break

                        if next_link:
                            await next_link.click()
                            await asyncio.sleep(3)
                            loaded_more = True
                            logger.debug("Navigated to next page")
                    except Exception as e:
                        logger.debug(f"Failed to navigate to next page: {e}")

                # 如果所有方法都失败，停止加载
                if not loaded_more:
                    logger.debug("No more content to load")
                    break

                page_num += 1

                # 安全上限检查
                if len(articles_list) > 1000:
                    logger.warning("Reached safety limit of 1000 articles")
                    break

            return articles_list

        except Exception as e:
            logger.error(f"Failed to scrape articles list: {e}", exc_info=True)
            return []
        finally:
            if page:
                await page.close()

    async def _fetch_article_content(self, article_url: str) -> Optional[str]:
        """
        访问文章详情页，获取完整内容

        Args:
            article_url: 文章URL

        Returns:
            完整的文章内容
        """
        # 相对URL补全
        if article_url.startswith('/'):
            article_url = f"https://thefuturesociety.org{article_url}"

        detail_page: Optional[Page] = None
        try:
            detail_page = await self._browser.new_page()

            await detail_page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            })

            await detail_page.goto(article_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # 提取文章正文内容
            # WordPress常见内容容器
            paragraphs = await detail_page.query_selector_all(
                'article p, .entry-content p, .post-content p, .content p, main p, .fl-rich-text p'
            )
            content_parts = []

            for para in paragraphs:
                para_text = (await para.inner_text()).strip()
                # 过滤掉非正文内容
                if para_text and len(para_text) > 10:
                    # 排除导航、分享按钮等
                    if para_text not in ['Share', 'Download', 'Print', 'Read More', 'Subscribe', '']:
                        # 排除短作者信息行（通常包含逗号且<30字符）
                        if len(para_text) > 30 or ',' not in para_text:
                            content_parts.append(para_text)

            full_content = '\n\n'.join(content_parts)
            return full_content if full_content else None

        except Exception as e:
            logger.error(f"获取文章详情失败 {article_url}: {e}")
            return None
        finally:
            if detail_page:
                await detail_page.close()

    async def _extract_article_from_element(self, article_elem) -> Optional[Dict[str, Any]]:
        """
        从文章元素中提取数据

        Args:
            article_elem: DOM元素

        Returns:
            文章数据字典
        """
        try:
            # 提取标题和URL
            # 多种可能的标题选择器
            title_link_elem = await article_elem.query_selector(
                "h2 a, h3 a, .entry-title a, .post-title a, a[rel='bookmark']"
            )

            if not title_link_elem:
                # 如果没有链接，尝试直接找标题
                title_elem = await article_elem.query_selector("h2, h3, .entry-title, .post-title")
                if title_elem:
                    title = (await title_elem.inner_text()).strip()
                    # 尝试在父元素中找链接
                    url_elem = await article_elem.query_selector("a[href]")
                    url = await url_elem.get_attribute("href") if url_elem else None
                else:
                    return None
            else:
                url = await title_link_elem.get_attribute("href")
                title = (await title_link_elem.inner_text()).strip()

            if not url or not title:
                return None

            # URL补全
            if url.startswith('/'):
                url = f"https://thefuturesociety.org{url}"

            # 提取摘要/描述
            summary_elem = await article_elem.query_selector(".entry-summary, .excerpt, .description, p")
            summary = None
            if summary_elem:
                summary = (await summary_elem.inner_text()).strip()

            # 提取日期
            date_elem = await article_elem.query_selector("time, .date, .published, .post-date")
            published_at = datetime.now()
            if date_elem:
                date_text = await date_elem.get_attribute("datetime")
                if not date_text:
                    date_text = (await date_elem.inner_text()).strip()
                published_at = self._parse_date(date_text)

            # 提取作者
            author_elem = await article_elem.query_selector(".author, .by-author, .post-author")
            provider = None
            if author_elem:
                provider = (await author_elem.inner_text()).strip()
                # 清理"By "前缀
                provider = re.sub(r'^By\s+', '', provider, flags=re.IGNORECASE)

            # 提取内容类型
            type_elem = await article_elem.query_selector(".category, .post-type, .content-type")
            content_type = None
            if type_elem:
                content_type = (await type_elem.inner_text()).strip()

            external_id = self._extract_id_from_url(url)

            return {
                "external_id": external_id,
                "title": title,
                "content": summary or title,
                "summary": summary,
                "provider": provider,
                "published_at": published_at,
                "url": url,
                "region": self.region,
                "content_type": content_type,
                "language": self.language
            }
        except Exception as e:
            logger.error(f"Failed to extract article from element: {e}")
            return None

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取文章ID

        Args:
            url: 文章URL，如 /aiagentsintheeu/ 或 /briefing-a-list-of-ai-governance-levers/

        Returns:
            文章路径slug作为ID
        """
        try:
            match = re.search(r'/([^/]+)/?$', url)
            return match.group(1) if match else None
        except Exception:
            return None

    def _parse_date(self, date_text: str) -> datetime:
        """
        解析日期文本

        Args:
            date_text: 日期文本，多种格式

        Returns:
            datetime对象
        """
        try:
            # 尝试ISO格式
            if 'T' in date_text:
                return datetime.fromisoformat(date_text.replace('Z', '+00:00'))

            # 尝试多种英文格式
            for fmt in [
                '%Y-%m-%d',
                '%B %d, %Y',
                '%b %d, %Y',
                '%d %B %Y',
                '%d %b %Y',
                '%m/%d/%Y',
                '%d/%m/%Y'
            ]:
                try:
                    return datetime.strptime(date_text.strip(), fmt)
                except ValueError:
                    continue

            logger.warning(f"Failed to parse date text '{date_text}'")
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
            items: 文章列表（已包含translated_summary）
        """
        try:
            with create_session() as db:
                for item in items:
                    message = FutureSocietyMessage(
                        id=str(uuid.uuid4()),
                        source_id=self.source_id,
                        external_id=item.get('external_id'),
                        title=item['title'],
                        content=item['content'],
                        summary=item.get('translated_summary', ''),
                        provider=item.get('provider'),
                        published_at=item.get('published_at'),
                        crawled_at=datetime.now(),
                        url=item['url'],
                        region=item.get('region'),
                        content_type=item.get('content_type'),
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
            items: 文章列表（已包含translated_summary）
        """
        if not self.chroma_storage or not self.embedding_client:
            return

        try:
            for item in items:
                summary = item.get('translated_summary', item.get('content', ''))
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
                        "content_type": item.get('content_type', ''),
                        "language": item.get('language', '')
                    }],
                    embeddings=[embedding]
                )
                logger.debug(f"Inserted to ChromaDB: url={item.get('url')}")
        except Exception as e:
            logger.error(f"Failed to store to ChromaDB: {e}")

    async def _generate_summary(self, summary: Optional[str], content: str) -> str:
        """
        生成摘要（支持中文翻译）

        外文内容自动翻译成中文，中文内容直接返回或截断

        Args:
            summary: 网页提取的摘要
            content: 正文内容

        Returns:
            摘要文本（中文）
        """
        # 1. 确定原始摘要来源
        source_text = summary if summary and len(summary.strip()) > 0 else content

        if not source_text:
            return ""

        # 2. 判断是否需要翻译（语言检测）
        if self.language == 'zh' or self._is_chinese(source_text):
            # 中文内容：直接返回或截断
            if len(source_text) <= 1000:
                return source_text
            return source_text[:1000] + "..."

        # 3. 外文内容：全文翻译成中文（不限制长度）
        if self.translator:
            try:
                translated = await self.translator.translate(
                    source_text,
                    context="The Future Society AI治理研究报告摘要"
                )
                return translated
            except Exception as e:
                logger.error(f"翻译失败: {e}")
                # 降级策略：返回截断原文
                return source_text[:500] + "... [AI翻译暂不可用]"
        else:
            # 无翻译器：返回截断原文
            if len(source_text) <= 1000:
                return source_text
            return source_text[:500] + "..."

    def _is_chinese(self, text: str) -> bool:
        """
        检测文本是否为中文

        Args:
            text: 待检测文本

        Returns:
            是否为中文
        """
        if not text:
            return False

        # 提取前200字符作为样本
        sample = text[:200]
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', sample))
        total_chars = len(sample)

        if total_chars == 0:
            return False

        # 中文字符占比>30%判定为中文
        return (chinese_chars / total_chars) > 0.3

    async def _close_browser(self) -> None:
        """关闭浏览器"""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.error(f"Failed to close browser: {e}")
