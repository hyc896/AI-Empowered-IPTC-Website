# -*- coding: utf-8 -*-

"""
FARI - AI for the Common Good Institute Collector
比利时AI公益研究所采集器

采集目标：
1. News & Media (https://www.fari.brussels/news-and-media/news)
2. Publications (https://www.fari.brussels/research-and-innovation/publications)

特点：
- 列表页无日期显示，需访问详情页获取日期和完整内容
- 使用分页机制加载更多内容
- 新闻和出版物存储到同一张表，通过content_type字段区分
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright
from sqlalchemy.exc import IntegrityError

from backend.database.entities import FARIMessage
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


class FARICollector:
    """FARI AI for the Common Good Institute采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - news_url: 新闻列表页URL
                - publications_url: 出版物列表页URL
                - source_id: 消息源ID
                - region: 地区（BE=Belgium）
                - language: 语言（en）
        """
        self.config = config
        self.interval = config.get('interval', 86400)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.news_url = config['config'].get('news_url', 'https://www.fari.brussels/news-and-media/news')
        self.publications_url = config['config'].get('publications_url', 'https://www.fari.brussels/research-and-innovation/publications')
        self.source_id = config.get('id', 'auto')
        self.region = config['config'].get('region', 'BE')
        self.language = config['config'].get('language', 'en')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【FARI】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【FARI】LLM服务不可用，将跳过向量化和翻译")

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

            logger.info(f"【FARI】采集器初始化成功")
            return True
        except Exception as e:
            logger.error(f"【FARI】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【FARI】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【FARI】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【FARI】采集失败: {e}", exc_info=True)

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        await self._close_browser()
        logger.info("【FARI】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新记录URL
        2. 并发采集News和Publications
        3. 过滤已存在URL
        4. 访问详情页获取完整内容和日期
        5. 存储到MySQL + ChromaDB
        """
        try:
            latest_url = await self._get_latest_stored_url()
            logger.debug(f"Latest stored URL: {latest_url}")

            # 并发采集新闻和出版物
            news_task = self._scrape_list(self.news_url, "News", latest_url)
            publications_task = self._scrape_list(self.publications_url, "Publication", latest_url)

            news_list, publications_list = await asyncio.gather(
                news_task,
                publications_task,
                return_exceptions=True
            )

            # 处理异常结果
            if isinstance(news_list, Exception):
                logger.error(f"【FARI】新闻采集失败: {news_list}")
                news_list = []
            if isinstance(publications_list, Exception):
                logger.error(f"【FARI】出版物采集失败: {publications_list}")
                publications_list = []

            # 合并所有新项目
            all_items = news_list + publications_list

            if not all_items:
                logger.debug("No new items to collect")
                return

            new_items = self._filter_new_items(all_items, latest_url)

            if new_items:
                # 访问详情页获取完整内容和日期
                logger.info(f"【FARI】开始访问 {len(new_items)} 篇文章/出版物的详情页...")
                for idx, item in enumerate(new_items, 1):
                    try:
                        detail_data = await self._fetch_detail_content(item['url'], item['content_type'])
                        if detail_data:
                            item.update(detail_data)
                            logger.debug(f"[{idx}/{len(new_items)}] ✓ 获取详情: {item['title'][:30]}...")
                        else:
                            logger.debug(f"[{idx}/{len(new_items)}] ⚠ 详情页访问失败，使用列表页数据")
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"[{idx}/{len(new_items)}] ✗ 详情页访问失败: {e}")

                await self._store_items(new_items)
                logger.info(f"【FARI】采集到 {len(new_items)} 条新记录 (News: {sum(1 for i in new_items if i.get('content_type') == 'News')}, Publications: {sum(1 for i in new_items if i.get('content_type') != 'News')})")
            else:
                logger.debug("【FARI】所有内容已存在，无新数据")

        except Exception as e:
            logger.error(f"【FARI】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新记录的URL

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(FARIMessage).filter(
                    FARIMessage.source_id == self.source_id,
                    FARIMessage.url.isnot(None)
                ).order_by(
                    FARIMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL: {e}")
            return None

    async def _scrape_list(
        self,
        list_url: str,
        content_type: str,
        latest_url: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        爬取列表页（新闻或出版物）

        Args:
            list_url: 列表页URL
            content_type: 内容类型（News/Publication）
            latest_url: 最新已存储的URL，遇到此URL立即停止

        Returns:
            项目列表
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

                await page.goto(list_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"【FARI {content_type}】第 {attempt + 1} 次尝试失败: {e}，{retry_delay}秒后重试...")
                    if page:
                        await page.close()
                        page = None
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【FARI {content_type}】所有重试均失败: {e}", exc_info=True)
                    if page:
                        await page.close()
                    return []

        if not page:
            return []

        try:
            # 等待内容加载
            if content_type == "News":
                # 新闻页使用网格布局
                await page.wait_for_selector("a[href*='news-and-media-article']", timeout=15000)
                items_selector = "a[href*='news-and-media-article']"
            else:
                # 出版物页使用publication路径
                await page.wait_for_selector("a[href*='/publication/']", timeout=15000)
                items_selector = "a[href*='/publication/']"

            items_list = []
            seen_urls = set()

            # 只采集第一页（分页处理可后续增强）
            item_elements = await page.query_selector_all(items_selector)
            logger.debug(f"【FARI {content_type}】Found {len(item_elements)} items on page")

            for item_elem in item_elements:
                try:
                    # 提取URL和标题
                    url = await item_elem.get_attribute("href")
                    if not url:
                        continue

                    # 处理相对URL
                    if url.startswith('/'):
                        url = f"https://www.fari.brussels{url}"

                    # 去重
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # 遇到最新URL立即停止
                    if latest_url and url == latest_url:
                        logger.debug(f"Reached latest stored URL ({latest_url}), stopping")
                        break

                    # 提取标题（从链接文本或子元素）
                    title_text = await item_elem.inner_text()
                    title = title_text.strip() if title_text else "Untitled"

                    # 如果标题太短，尝试从父元素获取
                    if len(title) < 10:
                        parent = await item_elem.evaluate_handle("el => el.closest('article, div, section')")
                        if parent:
                            full_text = await parent.inner_text()
                            title = full_text.split('\n')[0][:500]

                    external_id = self._extract_id_from_url(url)

                    items_list.append({
                        "external_id": external_id,
                        "title": title,
                        "content": title,
                        "summary": None,
                        "provider": None,
                        "published_at": None,
                        "url": url,
                        "region": self.region,
                        "content_type": content_type,
                        "language": self.language,
                        "tags": None,
                        "pdf_url": None
                    })

                except Exception as e:
                    logger.error(f"Failed to extract item: {e}")
                    continue

            logger.info(f"【FARI {content_type}】采集到 {len(items_list)} 条列表项")
            return items_list

        except Exception as e:
            logger.error(f"【FARI {content_type}】列表页爬取失败: {e}", exc_info=True)
            return []
        finally:
            if page:
                await page.close()

    async def _fetch_detail_content(
        self,
        article_url: str,
        content_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        访问详情页，获取完整内容、日期、作者等信息

        Args:
            article_url: 文章URL
            content_type: 内容类型（News/Publication）

        Returns:
            详情数据字典
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

            # 提取发布日期（从Schema.org metadata或页面显示）
            published_at = None
            try:
                # 尝试从Schema.org获取
                date_meta = await detail_page.query_selector('meta[property="article:published_time"], time[datetime]')
                if date_meta:
                    date_str = await date_meta.get_attribute("content") or await date_meta.get_attribute("datetime")
                    if date_str:
                        published_at = self._parse_date(date_str)
            except Exception as e:
                logger.debug(f"无法提取日期: {e}")

            # 如果没有日期，使用当前时间
            if not published_at:
                published_at = datetime.now()

            # 提取作者（从byline或Schema.org）
            provider = None
            try:
                # 查找作者元素
                author_elems = await detail_page.query_selector_all('[class*="author"], [class*="byline"], [rel="author"]')
                authors = []
                for elem in author_elems:
                    author_text = (await elem.inner_text()).strip()
                    if author_text and len(author_text) < 100:
                        # 清理"by"前缀
                        author_text = re.sub(r'^(by|By|BY)\s+', '', author_text)
                        authors.append(author_text)
                if authors:
                    provider = ", ".join(authors[:5])
            except Exception as e:
                logger.debug(f"无法提取作者: {e}")

            # 提取正文内容
            content_parts = []
            try:
                # 使用多种选择器尝试提取正文
                paragraphs = await detail_page.query_selector_all(
                    'article p, .content-wrapper p, .entry-content p, main p, [class*="content"] p'
                )

                for para in paragraphs:
                    para_text = (await para.inner_text()).strip()
                    if para_text and len(para_text) > 15:
                        # 过滤掉非正文内容
                        if not any(skip in para_text.lower() for skip in ['share', 'cookie', 'subscribe', 'newsletter', 'follow us']):
                            # 排除短作者信息行
                            if len(para_text) > 40 or ',' not in para_text:
                                content_parts.append(para_text)

                full_content = '\n\n'.join(content_parts)
            except Exception as e:
                logger.error(f"提取正文内容失败: {e}")
                full_content = ""

            # 提取PDF链接（出版物）
            pdf_url = None
            if content_type != "News":
                try:
                    pdf_link = await detail_page.query_selector('a[href*=".pdf"], a:has-text("Download")')
                    if pdf_link:
                        pdf_url = await pdf_link.get_attribute("href")
                        if pdf_url and not pdf_url.startswith('http'):
                            pdf_url = f"https://www.fari.brussels{pdf_url}" if pdf_url.startswith('/') else f"https://content.fari.brussels/{pdf_url}"
                except Exception as e:
                    logger.debug(f"无法提取PDF链接: {e}")

            # 提取主题标签（出版物）
            tags = None
            if content_type != "News":
                try:
                    tag_elems = await detail_page.query_selector_all('[class*="tag"], [class*="topic"], .chip')
                    tag_list = []
                    for elem in tag_elems:
                        tag_text = (await elem.inner_text()).strip()
                        if tag_text and len(tag_text) < 50:
                            tag_list.append(tag_text)
                    if tag_list:
                        tags = tag_list
                except Exception as e:
                    logger.debug(f"无法提取标签: {e}")

            return {
                "content": full_content if full_content else "No content available",
                "published_at": published_at,
                "provider": provider,
                "pdf_url": pdf_url,
                "tags": tags
            }

        except Exception as e:
            logger.error(f"获取详情失败 {article_url}: {e}")
            return None
        finally:
            if detail_page:
                await detail_page.close()

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取ID

        Args:
            url: 文章URL，如 /news-and-media-article/european-ai-week-2025

        Returns:
            文章路径slug作为ID
        """
        try:
            match = re.search(r'/([^/]+)/?$', url)
            return match.group(1) if match else None
        except Exception:
            return None

    def _parse_date(self, date_str: str) -> datetime:
        """
        解析日期字符串

        Args:
            date_str: 日期字符串，如 "2025-03-26T10:24:16+00:00"

        Returns:
            datetime对象
        """
        try:
            # 尝试ISO 8601格式
            if 'T' in date_str:
                # 移除时区信息以简化解析
                date_str = date_str.split('+')[0].split('Z')[0]
                return datetime.fromisoformat(date_str)

            # 尝试其他常见格式
            for fmt in ['%B %d, %Y', '%b %d, %Y', '%Y-%m-%d', '%d/%m/%Y']:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue

            logger.warning(f"Failed to parse date text '{date_str}'")
            return datetime.now()
        except Exception as e:
            logger.error(f"Failed to parse date text '{date_str}': {e}")
            return datetime.now()

    def _filter_new_items(
        self,
        items_list: List[Dict[str, Any]],
        latest_url: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        过滤已存在的项目

        Args:
            items_list: 项目列表
            latest_url: 最新已存储URL

        Returns:
            新项目列表
        """
        if not latest_url:
            return items_list

        new_items = []
        for item in items_list:
            if item.get('url') == latest_url:
                break
            new_items.append(item)

        return new_items

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        """
        并发存储到MySQL和ChromaDB

        Args:
            items: 项目列表
        """
        mysql_task = self._store_to_mysql(items)
        chroma_task = self._store_to_chroma(items)
        await asyncio.gather(mysql_task, chroma_task, return_exceptions=True)

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到MySQL

        Args:
            items: 项目列表
        """
        try:
            with create_session() as db:
                for item in items:
                    summary = await self._generate_summary(item.get('summary'), item.get('content', ''))

                    message = FARIMessage(
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
                        content_type=item.get('content_type'),
                        language=item.get('language'),
                        tags=item.get('tags'),
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
            items: 项目列表
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

        # 3. 外文内容：翻译成中文
        if self.translator:
            try:
                # 全文翻译（不限制长度，信任translator内部处理）
                translated = await self.translator.translate(
                    source_text,
                    context="FARI AI for the Common Good Institute研究文章或新闻摘要"
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
