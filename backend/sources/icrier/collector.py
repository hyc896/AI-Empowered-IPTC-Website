# -*- coding: utf-8 -*-

"""
ICRIER (Indian Council for Research on International Economic Relations) Collector
印度国际经济关系研究委员会采集器
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright
from sqlalchemy.exc import IntegrityError

from backend.database.entities import ICRIERMessage
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


class ICRIERCollector:
    """ICRIER出版物采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - url: ICRIER出版物页URL
                - source_id: 消息源ID（关联message_sources表）
                - region: 地区（IN=India）
                - language: 语言（en）
        """
        self.config = config
        self.interval = config.get('interval', 86400)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.url = config['config'].get('url', 'https://icrier.org/publication/')
        self.source_id = config.get('id', 'auto')
        self.region = config['config'].get('region', 'IN')
        self.language = config['config'].get('language', 'en')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【ICRIER】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【ICRIER】LLM服务不可用，将跳过向量化和翻译")

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

            logger.info(f"【ICRIER】采集器初始化成功: {self.url}")
            return True
        except Exception as e:
            logger.error(f"【ICRIER】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【ICRIER】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【ICRIER】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【ICRIER】采集失败: {e}")

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        await self._close_browser()
        logger.info("【ICRIER】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新文章URL
        2. Playwright爬取出版物列表页
        3. 遇到已存在URL时停止
        4. 访问详情页获取完整摘要
        5. 翻译并存储到MySQL + ChromaDB
        """
        try:
            latest_url = await self._get_latest_stored_url()
            logger.debug(f"Latest stored URL: {latest_url}")

            publications_list = await self._scrape_publications_list(latest_url)

            if not publications_list:
                logger.debug("No new items to collect")
                return

            # 访问详情页获取完整摘要
            logger.info(f"【ICRIER】开始访问 {len(publications_list)} 篇出版物的详情页...")
            for idx, item in enumerate(publications_list, 1):
                try:
                    detail_data = await self._fetch_publication_detail(item['url'])
                    if detail_data:
                        item['content'] = detail_data.get('content', item['content'])
                        if detail_data.get('provider'):
                            item['provider'] = detail_data['provider']
                        if detail_data.get('pdf_url'):
                            item['pdf_url'] = detail_data['pdf_url']
                        logger.debug(f"[{idx}/{len(publications_list)}] ✓ 获取详情: {item['url']}")
                    else:
                        logger.debug(f"[{idx}/{len(publications_list)}] ⚠ 保持列表页数据: {item['url']}")
                except Exception as e:
                    logger.error(f"[{idx}/{len(publications_list)}] ✗ 详情页访问失败: {e}")

            await self._store_items(publications_list)
            logger.info(f"【ICRIER】采集到 {len(publications_list)} 篇新出版物")

        except Exception as e:
            logger.error(f"【ICRIER】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新出版物的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(ICRIERMessage).filter(
                    ICRIERMessage.source_id == self.source_id,
                    ICRIERMessage.url.isnot(None)
                ).order_by(
                    ICRIERMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL: {e}")
            return None

    async def _scrape_publications_list(self, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        Playwright爬取出版物列表页

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
                    logger.warning(f"【ICRIER】第 {attempt + 1} 次尝试失败: {e}，{retry_delay}秒后重试...")
                    if page:
                        await page.close()
                        page = None
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【ICRIER】所有重试均失败: {e}", exc_info=True)
                    if page:
                        await page.close()
                    return []

        if not page:
            return []

        try:
            # ICRIER使用卡片式布局展示出版物
            # 尝试多种可能的选择器
            await page.wait_for_timeout(3000)

            # 尝试检测出版物容器
            publication_selector = None
            possible_selectors = [
                'article',
                '.publication-item',
                '.post',
                '.entry',
                'div[class*="publication"]',
                'div[class*="post"]'
            ]

            for selector in possible_selectors:
                elements = await page.query_selector_all(selector)
                if elements and len(elements) > 0:
                    publication_selector = selector
                    logger.debug(f"Found {len(elements)} publications using selector: {selector}")
                    break

            if not publication_selector:
                logger.error("【ICRIER】未找到出版物列表元素")
                return []

            publication_elements = await page.query_selector_all(publication_selector)
            logger.debug(f"Found {len(publication_elements)} publication elements")

            publications_list = []
            for elem in publication_elements:
                pub_data = await self._extract_publication_from_element(elem, page)

                if not pub_data:
                    continue

                pub_url = pub_data.get('url')
                if not pub_url:
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

    async def _extract_publication_from_element(self, elem, page: Page) -> Optional[Dict[str, Any]]:
        """
        从出版物元素中提取数据

        Args:
            elem: 出版物DOM元素
            page: Playwright Page对象

        Returns:
            出版物数据字典
        """
        try:
            # 提取标题和URL
            title_link = await elem.query_selector("a[href*='/publications/'], h2 a, h3 a, .title a")
            if not title_link:
                return None

            url = await title_link.get_attribute("href")
            title = (await title_link.inner_text()).strip()

            if not url or not title:
                return None

            # 补全相对URL
            if url.startswith('/'):
                url = f"https://icrier.org{url}"

            # 提取分类（Policy Briefs/Reports等）
            category_elem = await elem.query_selector(".category, .type, .publication-type, [class*='category']")
            category = ""
            if category_elem:
                category = (await category_elem.inner_text()).strip()

            # 提取日期
            date_elem = await elem.query_selector(".date, time, [class*='date'], [class*='published']")
            published_at = datetime.now()
            if date_elem:
                date_text = (await date_elem.inner_text()).strip()
                published_at = self._parse_date(date_text)

            external_id = self._extract_id_from_url(url)

            return {
                "external_id": external_id,
                "title": title,
                "content": title,
                "provider": None,
                "published_at": published_at,
                "url": url,
                "region": self.region,
                "category": category,
                "language": self.language,
                "pdf_url": None
            }
        except Exception as e:
            logger.error(f"Failed to extract publication from element: {e}")
            return None

    async def _fetch_publication_detail(self, publication_url: str) -> Optional[Dict[str, Any]]:
        """
        访问出版物详情页，获取完整摘要和作者信息

        Args:
            publication_url: 出版物URL

        Returns:
            包含content、provider、pdf_url的字典
        """
        detail_page: Optional[Page] = None
        try:
            detail_page = await self._browser.new_page()

            await detail_page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            })

            await detail_page.goto(publication_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # 提取摘要内容
            paragraphs = await detail_page.query_selector_all('article p, .content p, .entry-content p, main p')
            content_parts = []

            for para in paragraphs:
                para_text = (await para.inner_text()).strip()
                if para_text and len(para_text) > 30:
                    # 排除非正文内容
                    if not any(keyword in para_text.lower() for keyword in ['share', 'download', 'print', 'author(s)']):
                        content_parts.append(para_text)

            full_content = '\n\n'.join(content_parts[:3]) if content_parts else None

            # 提取作者
            author_links = await detail_page.query_selector_all('a[href*="/people/"]')
            authors = []
            for author_link in author_links:
                author_name = (await author_link.inner_text()).strip()
                if author_name and author_name not in authors:
                    authors.append(author_name)
            provider = ", ".join(authors) if authors else None

            # 提取PDF链接
            pdf_link = await detail_page.query_selector('a[href*=".pdf"]')
            pdf_url = None
            if pdf_link:
                pdf_url = await pdf_link.get_attribute("href")
                if pdf_url and not pdf_url.startswith('http'):
                    pdf_url = f"https://icrier.org{pdf_url}"

            return {
                "content": full_content,
                "provider": provider,
                "pdf_url": pdf_url
            }

        except Exception as e:
            logger.error(f"获取出版物详情失败 {publication_url}: {e}")
            return None
        finally:
            if detail_page:
                await detail_page.close()

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取出版物ID

        Args:
            url: 出版物URL

        Returns:
            URL slug作为ID
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
            date_text: 日期文本

        Returns:
            datetime对象
        """
        try:
            for fmt in ['%B %d, %Y', '%b %d, %Y', '%B, %Y', '%b, %Y', '%Y-%m-%d', '%d/%m/%Y']:
                try:
                    return datetime.strptime(date_text.strip(), fmt)
                except ValueError:
                    continue

            logger.warning(f"Failed to parse date text '{date_text}'")
            return datetime.now()
        except Exception as e:
            logger.error(f"Failed to parse date text '{date_text}': {e}")
            return datetime.now()

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
        存储到MySQL（预翻译模式）

        Args:
            items: 出版物列表
        """
        try:
            # 预翻译所有摘要（在session外执行）
            summaries = []
            for item in items:
                summary = await self._generate_summary(None, item.get('content', ''))
                summaries.append(summary)

            # 批量插入数据库
            with create_session() as db:
                for idx, item in enumerate(items):
                    message = ICRIERMessage(
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
                        category=item.get('category'),
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
                summary = await self._generate_summary(None, item.get('content', ''))
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

        # 3. 外文内容：翻译成中文
        if self.translator:
            try:
                translated = await self.translator.translate(
                    source_text,
                    context="ICRIER印度智库研究出版物摘要"
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
