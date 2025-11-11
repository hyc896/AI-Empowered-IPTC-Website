# -*- coding: utf-8 -*-

"""
CSET (Center for Security and Emerging Technology) Collector
安全与新兴技术中心研究论文采集器（乔治城大学）
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright
from sqlalchemy.exc import IntegrityError

from backend.database.entities import CSETMessage
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


class CSETCollector:
    """CSET (Georgetown University) 研究论文采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - url: CSET CyberAI页面URL
                - source_id: 消息源ID（关联message_sources表）
                - region: 地区（US）
                - language: 语言（en）
        """
        self.config = config
        self.interval = config.get('interval', 86400)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.url = config['config'].get('url', 'https://cset.georgetown.edu/publications/?fwp_topic=cyberai')
        self.source_id = config.get('id', 'auto')
        self.region = config['config'].get('region', 'US')
        self.language = config['config'].get('language', 'en')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【CSET】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【CSET】LLM服务不可用，将跳过向量化和翻译")

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

            logger.info(f"【CSET】采集器初始化成功: {self.url}")
            return True
        except Exception as e:
            logger.error(f"【CSET】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【CSET】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【CSET】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【CSET】采集失败: {e}")

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        await self._close_browser()
        logger.info("【CSET】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新论文URL
        2. Playwright爬取publications列表页
        3. 过滤已存在URL
        4. 访问详情页获取完整content
        5. 翻译英文摘要为中文
        6. 并发存储到MySQL + ChromaDB
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
                logger.info(f"【CSET】开始访问 {len(new_items)} 篇文章的详情页...")
                for idx, item in enumerate(new_items, 1):
                    try:
                        full_content = await self._fetch_article_content(item['url'])
                        if full_content:
                            item['content'] = full_content
                            logger.debug(f"[{idx}/{len(new_items)}] ✓ 获取完整内容: {item['url']}")
                        else:
                            logger.debug(f"[{idx}/{len(new_items)}] ⚠ 保持使用摘要: {item['url']}")
                    except Exception as e:
                        logger.error(f"[{idx}/{len(new_items)}] ✗ 详情页访问失败: {e}")

                await self._store_items(new_items)
                logger.info(f"【CSET】采集到 {len(new_items)} 篇新文章")
            else:
                logger.debug("【CSET】所有文章已存在，无新数据")

        except Exception as e:
            logger.error(f"【CSET】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新论文的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(CSETMessage).filter(
                    CSETMessage.source_id == self.source_id,
                    CSETMessage.url.isnot(None)
                ).order_by(
                    CSETMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL: {e}")
            return None

    async def _scrape_publications_list(self, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        Playwright爬取publications列表页，提取文章列表

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
                    logger.warning(f"【CSET】第 {attempt + 1} 次尝试失败: {e}，{retry_delay}秒后重试...")
                    if page:
                        await page.close()
                        page = None
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【CSET】所有重试均失败: {e}", exc_info=True)
                    if page:
                        await page.close()
                    return []

        if not page:
            return []

        try:
            # 全量加载：滚动/点击加载更多
            # CSET使用动态链接，先加载所有内容
            item_selector = 'a[href*="/publication/"], a[href*="/article/"]'
            final_count = await PageLoader.load_all_content(
                page=page,
                item_selector=item_selector,
                max_scrolls=30,
                scroll_delay=3.0,
                load_more_selectors=[
                    'button:has-text("Load More")',
                    'a:has-text("Show More")',
                    '[class*="load-more"]',
                    '[class*="show-more"]'
                ]
            )
            logger.info(f"【CSET】全量加载完成，共发现 {final_count} 个链接")

            # 使用JavaScript提取publications列表
            publications_data = await page.evaluate("""
                () => {
                    const publications = [];

                    // 查找所有publication或article链接
                    const allLinks = document.querySelectorAll('a[href*="/publication/"], a[href*="/article/"]');

                    // 使用Set去重（同一文章可能有多个链接）
                    const seenUrls = new Set();

                    allLinks.forEach(link => {
                        const href = link.href;
                        if (seenUrls.has(href)) return;
                        seenUrls.add(href);

                        // 找到包含完整信息的父容器
                        let container = link.closest('article, div[class*="publication"], div[class*="post"], li');
                        if (!container) container = link.parentElement;

                        // 提取标题
                        const titleElem = container.querySelector('h1, h2, h3, h4, [class*="title"]') || link;
                        const title = titleElem.textContent.trim();

                        if (!title || title.length < 5) return;

                        // 提取日期（匹配 "October 2025", "Oct 24, 2025" 等格式）
                        const dateRegex = /(January|February|March|April|May|June|July|August|September|October|November|December)\\s+(\\d{1,2},\\s+)?(\\d{4})/i;
                        const containerText = container.textContent;
                        const dateMatch = containerText.match(dateRegex);
                        const dateStr = dateMatch ? dateMatch[0] : '';

                        // 提取作者（通常在日期之后或之前）
                        let authors = '';
                        const textLines = containerText.split('\\n').map(l => l.trim()).filter(l => l && l.length > 3);
                        for (const line of textLines) {
                            // 作者行特征：包含逗号，长度适中，不包含日期
                            if (line.includes(',') && line.length > 10 && line.length < 300 && !line.match(dateRegex)) {
                                // 可能是作者列表（例如 "Kyle Miller, Mia Hoffmann, and Rebecca Gelles"）
                                if (!line.match(/^(Analysis|Report|Blog|Article|Event)/i)) {
                                    authors = line;
                                    break;
                                }
                            }
                        }

                        // 提取描述（通常在<p>标签中，长度适中）
                        const descElems = container.querySelectorAll('p');
                        let description = '';
                        for (const elem of descElems) {
                            const text = elem.textContent.trim();
                            // 描述特征：较长，不是日期，不是作者
                            if (text.length > 50 && text.length < 1500 && !text.match(dateRegex)) {
                                description = text;
                                break;
                            }
                        }

                        // 提取内容类型（Analysis, Report, Blog等）
                        const typeElem = container.querySelector('[class*="type"], [class*="category"], [class*="tag"]');
                        const contentType = typeElem ? typeElem.textContent.trim() : '';

                        publications.push({
                            title: title,
                            url: href,
                            dateStr: dateStr,
                            authors: authors,
                            description: description,
                            contentType: contentType
                        });
                    });

                    return publications;
                }
            """)

            publications_list = []
            for pub_data in publications_data:
                article_data = self._parse_publication_data(pub_data)
                if not article_data:
                    continue

                article_url = article_data.get('url')
                if not article_url:
                    continue

                # 去重检查
                if latest_url and article_url == latest_url:
                    logger.debug(f"Reached latest stored URL ({latest_url}), stopping")
                    break

                publications_list.append(article_data)

            logger.debug(f"Extracted {len(publications_list)} publications")
            return publications_list

        except Exception as e:
            logger.error(f"Failed to scrape publications list: {e}", exc_info=True)
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
            # CSET的文章内容通常在article, .entry-content, .post-content等容器中
            paragraphs = await detail_page.query_selector_all('article p, .entry-content p, .post-content p, main p')
            content_parts = []

            for para in paragraphs:
                para_text = (await para.inner_text()).strip()
                # 过滤掉非正文内容
                if para_text and len(para_text) > 20:
                    # 排除作者信息行（短文本+包含逗号）
                    if not (len(para_text) < 100 and para_text.count(',') >= 2):
                        content_parts.append(para_text)

            full_content = '\n\n'.join(content_parts)
            return full_content if full_content else None

        except Exception as e:
            logger.error(f"获取文章详情失败 {article_url}: {e}")
            return None
        finally:
            if detail_page:
                await detail_page.close()

    def _parse_publication_data(self, pub_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析publication数据

        Args:
            pub_data: JavaScript提取的原始数据

        Returns:
            标准化的文章数据字典
        """
        try:
            title = pub_data.get('title', '').strip()
            url = pub_data.get('url', '').strip()

            if not title or not url:
                return None

            # 解析日期
            date_str = pub_data.get('dateStr', '')
            published_at = self._parse_date_text(date_str) if date_str else datetime.now()

            # 提取external_id（从URL路径）
            external_id = self._extract_id_from_url(url)

            # 作者
            authors = pub_data.get('authors', '').strip()

            # 描述作为初始content
            description = pub_data.get('description', '').strip()
            if not description:
                description = title

            # 内容类型
            content_type = pub_data.get('contentType', 'Research')

            return {
                "external_id": external_id,
                "title": title,
                "content": description,
                "summary": description if len(description) <= 1000 else description[:1000] + "...",
                "provider": authors if authors else None,
                "published_at": published_at,
                "url": url,
                "region": self.region,
                "category": content_type,
                "language": self.language
            }
        except Exception as e:
            logger.error(f"Failed to parse publication data: {e}")
            return None

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取文章ID

        Args:
            url: 文章URL，如 https://cset.georgetown.edu/publication/the-use-of-open-models-in-research/

        Returns:
            文章路径slug作为ID
        """
        try:
            match = re.search(r'/(publication|article)/([^/]+)/?$', url)
            return match.group(2) if match else None
        except Exception:
            return None

    def _parse_date_text(self, date_text: str) -> datetime:
        """
        解析日期文本

        Args:
            date_text: 日期文本，如 "October 2025" 或 "Oct 24, 2025"

        Returns:
            datetime对象
        """
        try:
            # 尝试 "October 2025" 格式
            if ',' not in date_text:
                return datetime.strptime(date_text.strip(), '%B %Y')
            # 尝试 "Oct 24, 2025" 格式
            else:
                # 移除缩写月份的点号（如果有）
                date_text = date_text.replace('.', '')
                return datetime.strptime(date_text.strip(), '%B %d, %Y')
        except Exception:
            # 备用：尝试简写月份格式
            try:
                date_text = date_text.replace('.', '')
                if ',' in date_text:
                    return datetime.strptime(date_text.strip(), '%b %d, %Y')
                else:
                    return datetime.strptime(date_text.strip(), '%b %Y')
            except Exception as e:
                logger.error(f"Failed to parse date text '{date_text}': {e}")
                return datetime.now()

    def _filter_new_items(
        self,
        publications_list: List[Dict[str, Any]],
        latest_url: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        过滤已存在的文章

        Args:
            publications_list: 文章列表
            latest_url: 最新已存储URL

        Returns:
            新文章列表
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
                    message = CSETMessage(
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
                summary = item.get('summary', '')
                if not summary:
                    summary = self._generate_summary(None, item.get('content', ''))

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
        4. 外文：调用translator.translate()进行翻译（全文翻译，不限制长度）

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
                    context="AI安全研究论文"
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
