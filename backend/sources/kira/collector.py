# -*- coding: utf-8 -*-

"""
KIRA Center (Center for AI Risks & Impacts) Collector
德国AI风险与影响研究中心采集器
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright
from sqlalchemy.exc import IntegrityError

from backend.database.entities import KIRAMessage
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


class KIRACollector:
    """KIRA Center博客与报告采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - url: KIRA博客页URL
                - source_id: 消息源ID（关联message_sources表）
                - region: 地区（DE=Germany）
                - language: 语言（en/de）
        """
        self.config = config
        self.interval = config.get('interval', 86400)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.url = config['config'].get('url', 'https://kira.eu/blog')
        self.source_id = config.get('id', 'auto')
        self.region = config['config'].get('region', 'DE')
        self.language = config['config'].get('language', 'en')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【KIRA】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【KIRA】LLM服务不可用，将跳过向量化和翻译")

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

            logger.info(f"【KIRA】采集器初始化成功: {self.url}")
            return True
        except Exception as e:
            logger.error(f"【KIRA】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【KIRA】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【KIRA】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【KIRA】采集失败: {e}")

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        await self._close_browser()
        logger.info("【KIRA】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新文章URL
        2. Playwright爬取博客列表页
        3. 过滤已存在URL
        4. 访问详情页获取完整内容
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
                # 访问详情页获取完整content
                logger.info(f"【KIRA】开始访问 {len(new_items)} 篇文章的详情页...")
                for idx, item in enumerate(new_items, 1):
                    try:
                        full_content = await self._fetch_article_content(item['url'])
                        if full_content:
                            item['content'] = full_content
                            logger.debug(f"[{idx}/{len(new_items)}] ✓ 获取完整内容: {item['url']}")
                        else:
                            logger.debug(f"[{idx}/{len(new_items)}] ⚠ 保持使用摘要: {item['url']}")

                        # 提取PDF链接（如果是报告）
                        pdf_url = await self._extract_pdf_url(item['url'])
                        if pdf_url:
                            item['pdf_url'] = pdf_url
                            logger.debug(f"[{idx}/{len(new_items)}] ✓ 找到PDF: {pdf_url}")

                        # 添加延迟避免反爬
                        await asyncio.sleep(2)
                    except Exception as e:
                        logger.error(f"[{idx}/{len(new_items)}] ✗ 详情页访问失败: {e}")

                await self._store_items(new_items)
                logger.info(f"【KIRA】采集到 {len(new_items)} 篇新文章")
            else:
                logger.debug("【KIRA】所有文章已存在，无新数据")

        except Exception as e:
            logger.error(f"【KIRA】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新文章的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(KIRAMessage).filter(
                    KIRAMessage.source_id == self.source_id,
                    KIRAMessage.url.isnot(None)
                ).order_by(
                    KIRAMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL: {e}")
            return None

    async def _scrape_articles_list(self, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        Playwright爬取博客列表页，提取文章列表

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
                    logger.warning(f"【KIRA】第 {attempt + 1} 次尝试失败: {e}，{retry_delay}秒后重试...")
                    if page:
                        await page.close()
                        page = None
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【KIRA】所有重试均失败: {e}", exc_info=True)
                    if page:
                        await page.close()
                    return []

        if not page:
            return []

        try:
            # KIRA博客使用Squarespace，文章列表在blog-item类中
            articles_selector = "article.blog-item, .blog-basic-grid article"
            await page.wait_for_selector(articles_selector, timeout=15000)

            article_elems = await page.query_selector_all(articles_selector)
            logger.debug(f"Found {len(article_elems)} articles")

            articles_list = []
            for article_elem in article_elems:
                article_data = await self._extract_article_from_element(article_elem)

                if not article_data:
                    continue

                article_url = article_data.get('url')
                if not article_url:
                    continue

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

    async def _extract_article_from_element(self, article_elem) -> Optional[Dict[str, Any]]:
        """
        从文章元素中提取数据

        Args:
            article_elem: <article> DOM元素

        Returns:
            文章数据字典
        """
        try:
            # 提取标题和URL
            title_link_elem = await article_elem.query_selector("a.blog-title-link, h1.blog-title a, .blog-item-title a")
            if not title_link_elem:
                return None

            url = await title_link_elem.get_attribute("href")
            title_elem = await article_elem.query_selector(".blog-title, .blog-item-title, h1")
            title = (await title_elem.inner_text()).strip() if title_elem else ""

            if not url or not title:
                return None

            # 完整URL
            if not url.startswith('http'):
                url = f"https://kira.eu{url}"

            # 提取日期
            date_elem = await article_elem.query_selector("time.blog-date, time.blog-meta-item--date, .blog-meta-item--date")
            published_at = datetime.now()
            if date_elem:
                date_text = (await date_elem.inner_text()).strip()
                published_at = self._parse_date(date_text)

            # 提取作者
            author_elem = await article_elem.query_selector(".blog-author, .blog-meta-item--author")
            provider = None
            if author_elem:
                author_text = (await author_elem.inner_text()).strip()
                # 移除"by"前缀
                provider = author_text.replace("by ", "").strip()

            # 提取摘要/excerpt
            excerpt_elem = await article_elem.query_selector(".blog-excerpt, .blog-item-content-wrapper p")
            excerpt = ""
            if excerpt_elem:
                excerpt = (await excerpt_elem.inner_text()).strip()

            external_id = self._extract_id_from_url(url)

            return {
                "external_id": external_id,
                "title": title,
                "content": excerpt if excerpt else title,
                "summary": None,
                "provider": provider,
                "published_at": published_at,
                "url": url,
                "region": self.region,
                "language": self.language,
                "content_type": "Blog"
            }
        except Exception as e:
            logger.error(f"Failed to extract article from element: {e}")
            return None

    async def _fetch_article_content(self, article_url: str) -> Optional[str]:
        """
        访问文章详情页，获取完整内容

        Args:
            article_url: 文章URL

        Returns:
            完整的文章内容
        """
        detail_page: Optional[Page] = None
        try:
            detail_page = await self._browser.new_page()

            await detail_page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            })

            await detail_page.goto(article_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # 提取文章正文内容（Squarespace结构）
            paragraphs = await detail_page.query_selector_all('.sqs-block-content p, article .entry-content p, .blog-item-content-wrapper p')
            content_parts = []

            for para in paragraphs:
                para_text = (await para.inner_text()).strip()
                # 过滤掉非正文内容
                if para_text and len(para_text) > 20:
                    # 排除常见非正文内容
                    if not any(skip in para_text.lower() for skip in ['share', 'subscribe', 'newsletter', 'follow us']):
                        content_parts.append(para_text)

            full_content = '\n\n'.join(content_parts)
            return full_content if full_content else None

        except Exception as e:
            logger.error(f"获取文章详情失败 {article_url}: {e}")
            return None
        finally:
            if detail_page:
                await detail_page.close()

    async def _extract_pdf_url(self, article_url: str) -> Optional[str]:
        """
        从文章页提取PDF下载链接（如果是报告）

        Args:
            article_url: 文章URL

        Returns:
            PDF链接
        """
        detail_page: Optional[Page] = None
        try:
            detail_page = await self._browser.new_page()
            await detail_page.goto(article_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # 查找PDF链接
            pdf_link_elem = await detail_page.query_selector("a[href$='.pdf'], a[href*='/s/'][href*='.pdf']")
            if pdf_link_elem:
                pdf_url = await pdf_link_elem.get_attribute("href")
                if pdf_url and not pdf_url.startswith('http'):
                    pdf_url = f"https://kira.eu{pdf_url}"
                return pdf_url
            return None

        except Exception as e:
            logger.debug(f"提取PDF链接失败 {article_url}: {e}")
            return None
        finally:
            if detail_page:
                await detail_page.close()

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取文章ID

        Args:
            url: 文章URL，如 https://kira.eu/blog/compute/eng

        Returns:
            文章路径slug作为ID
        """
        try:
            # 提取/blog/后的路径部分
            match = re.search(r'/blog/([^/?]+)', url)
            if match:
                return match.group(1)
            # 备用：提取最后一段路径
            match = re.search(r'/([^/]+)/?$', url)
            return match.group(1) if match else None
        except Exception:
            return None

    def _parse_date(self, date_text: str) -> datetime:
        """
        解析日期文本

        Args:
            date_text: 日期文本，如 "14.10.25" 或 "October 14, 2025"

        Returns:
            datetime对象
        """
        try:
            # 尝试德式格式 DD.MM.YY
            if re.match(r'\d{2}\.\d{2}\.\d{2}', date_text):
                parts = date_text.split('.')
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                # 假设20xx年
                year = 2000 + year if year < 100 else year
                return datetime(year, month, day)

            # 尝试英文格式
            for fmt in ['%B %d, %Y', '%b %d, %Y', '%Y-%m-%d', '%d/%m/%Y']:
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
        存储文章（先翻译，再存储到MySQL和ChromaDB）

        Args:
            items: 文章列表
        """
        # 预翻译所有摘要（在数据库会话外）
        translated_summaries = []
        for item in items:
            summary = await self._generate_summary(item.get('summary'), item.get('content', ''))
            translated_summaries.append(summary)

        # 存储到MySQL和ChromaDB
        await self._store_to_mysql(items, translated_summaries)
        await self._store_to_chroma(items, translated_summaries)

    async def _store_to_mysql(self, items: List[Dict[str, Any]], summaries: List[str]) -> None:
        """
        存储到MySQL

        Args:
            items: 文章列表
            summaries: 翻译后的摘要列表
        """
        try:
            with create_session() as db:
                for idx, item in enumerate(items):
                    message = KIRAMessage(
                        id=str(uuid.uuid4()),
                        source_id=self.source_id,
                        external_id=item.get('external_id'),
                        title=item['title'],
                        content=item['content'],
                        summary=summaries[idx],
                        provider=item.get('provider'),
                        published_at=item.get('published_at'),
                        crawled_at=datetime.now(),
                        url=item['url'],
                        region=item.get('region'),
                        content_type=item.get('content_type'),
                        language=item.get('language'),
                        pdf_url=item.get('pdf_url')
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

    async def _store_to_chroma(self, items: List[Dict[str, Any]], summaries: List[str]) -> None:
        """
        存储到ChromaDB

        Args:
            items: 文章列表
            summaries: 翻译后的摘要列表
        """
        if not self.chroma_storage or not self.embedding_client:
            return

        try:
            for idx, item in enumerate(items):
                document_text = f"{item['title']} {summaries[idx]}"

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
                    context="KIRA Center AI政策研究文章"
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
