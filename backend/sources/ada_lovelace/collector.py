# -*- coding: utf-8 -*-

"""
Ada Lovelace Institute Collector
Ada Lovelace Institute（英国AI治理与伦理智库）采集器
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright
from sqlalchemy.exc import IntegrityError

from backend.database.entities import AdaLovelaceMessage
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


class AdaLovelaceCollector:
    """Ada Lovelace Institute 博客采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - url: Ada Lovelace博客URL
                - source_id: 消息源ID（关联message_sources表）
                - region: 地区（UK）
                - language: 语言（en）
                - test_mode: 测试模式（True时只采集少量数据）
                - test_limit: 测试模式下的最大采集数量
        """
        self.config = config
        self.interval = config.get('interval', 86400)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.url = config['config'].get('url', 'https://www.adalovelaceinstitute.org/blog/')
        self.source_id = config.get('id', 'auto')
        self.region = config['config'].get('region', 'UK')
        self.language = config['config'].get('language', 'en')
        self.test_mode = config.get('test_mode', False)
        self.test_limit = config.get('test_limit', 5)

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【Ada Lovelace】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【Ada Lovelace】LLM服务不可用，将跳过向量化和翻译")

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

            logger.info(f"【Ada Lovelace】采集器初始化成功: {self.url}")
            return True
        except Exception as e:
            logger.error(f"【Ada Lovelace】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【Ada Lovelace】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【Ada Lovelace】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【Ada Lovelace】采集失败: {e}")

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        await self._close_browser()
        logger.info("【Ada Lovelace】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新文章URL
        2. Playwright爬取博客列表页（支持分页）
        3. 过滤已存在URL
        4. 访问详情页获取完整内容
        5. 翻译并存储到MySQL + ChromaDB
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
                # 测试模式：限制采集数量
                if self.test_mode and len(new_items) > self.test_limit:
                    logger.info(f"【Ada Lovelace】测试模式：限制采集数量为 {self.test_limit} 篇")
                    new_items = new_items[:self.test_limit]

                # 访问详情页获取完整content
                logger.info(f"【Ada Lovelace】开始访问 {len(new_items)} 篇文章的详情页...")
                for idx, item in enumerate(new_items, 1):
                    try:
                        full_content = await self._fetch_article_content(item['url'])
                        if full_content:
                            item['content'] = full_content
                            logger.debug(f"[{idx}/{len(new_items)}] ✓ 获取完整内容: {item['url']}")
                        else:
                            logger.debug(f"[{idx}/{len(new_items)}] ⚠ 保持使用标题: {item['url']}")

                        # 添加延迟避免触发反爬虫
                        await asyncio.sleep(2)
                    except Exception as e:
                        logger.error(f"[{idx}/{len(new_items)}] ✗ 详情页访问失败: {e}")

                await self._store_items(new_items)
                logger.info(f"【Ada Lovelace】采集到 {len(new_items)} 篇新文章")
            else:
                logger.debug("【Ada Lovelace】所有文章已存在，无新数据")

        except Exception as e:
            logger.error(f"【Ada Lovelace】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新文章的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(AdaLovelaceMessage).filter(
                    AdaLovelaceMessage.source_id == self.source_id,
                    AdaLovelaceMessage.url.isnot(None)
                ).order_by(
                    AdaLovelaceMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL: {e}")
            return None

    async def _scrape_articles_list(self, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        Playwright爬取博客列表页，支持分页加载

        Args:
            latest_url: 最新已存储的URL，遇到此URL立即停止

        Returns:
            文章列表
        """
        page: Optional[Page] = None
        articles_list = []
        current_page = 1
        max_pages = 10  # 安全上限：最多加载10页
        found_latest = False

        try:
            page = await self._browser.new_page()

            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            })

            while current_page <= max_pages and not found_latest:
                page_url = f"{self.url}?current-page={current_page}#listing" if current_page > 1 else self.url

                try:
                    await page.goto(page_url, wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(3)

                    # Ada Lovelace博客页面使用多种可能的选择器
                    # 尝试多种选择器策略
                    article_elements = []
                    selectors_to_try = [
                        ".wp-block-post-template > li",  # WordPress块布局
                        "article",  # 语义化HTML
                        "[id='listing'] article",  # 带listing ID的文章
                        "a[href*='/blog/']",  # 包含/blog/路径的链接
                    ]

                    for selector in selectors_to_try:
                        try:
                            await page.wait_for_selector(selector, timeout=5000)
                            elements = await page.query_selector_all(selector)
                            if len(elements) > 0:
                                article_elements = elements
                                logger.debug(f"Found {len(article_elements)} elements using selector: {selector}")
                                break
                        except Exception:
                            continue

                    if len(article_elements) == 0:
                        logger.warning(f"No articles found on page {current_page} with any selector")
                        break

                    # 根据选择器类型决定提取方法
                    for article_elem in article_elements:
                        # 如果选择器返回的是<a>标签，需要特殊处理
                        tag_name = await article_elem.evaluate("el => el.tagName.toLowerCase()")
                        if tag_name == 'a':
                            article_data = await self._extract_article_from_link(article_elem)
                        else:
                            article_data = await self._extract_article_from_element(article_elem)

                        if not article_data:
                            continue

                        article_url = article_data.get('url')
                        if not article_url:
                            continue

                        # 检查是否已到达最新存储的URL
                        if latest_url and article_url == latest_url:
                            logger.debug(f"Reached latest stored URL ({latest_url}), stopping")
                            found_latest = True
                            break

                        articles_list.append(article_data)

                    current_page += 1

                except Exception as e:
                    logger.error(f"Failed to scrape page {current_page}: {e}")
                    break

            return articles_list

        except Exception as e:
            logger.error(f"Failed to scrape articles list: {e}", exc_info=True)
            return []
        finally:
            if page:
                await page.close()

    async def _extract_article_from_link(self, link_elem) -> Optional[Dict[str, Any]]:
        """
        从链接元素中提取文章数据（简化版）

        Args:
            link_elem: <a> DOM元素

        Returns:
            文章数据字典
        """
        try:
            url = await link_elem.get_attribute("href")
            if not url or '/blog/' not in url:
                return None

            # 确保URL是完整的
            if not url.startswith('http'):
                url = f"https://www.adalovelaceinstitute.org{url}"

            # 提取标题（可能在链接文本或父元素中）
            title = (await link_elem.inner_text()).strip()
            if not title:
                # 尝试从父元素的h3中获取
                parent = await link_elem.evaluate_handle("el => el.closest('article') || el.parentElement")
                h3_elem = await parent.query_selector("h3")
                if h3_elem:
                    title = (await h3_elem.inner_text()).strip()

            if not title:
                return None

            external_id = self._extract_id_from_url(url)

            return {
                "external_id": external_id,
                "title": title,
                "content": title,
                "summary": None,
                "provider": None,
                "published_at": datetime.now(),
                "url": url,
                "region": self.region,
                "category": None,
                "language": self.language,
                "tags": None
            }
        except Exception as e:
            logger.error(f"Failed to extract article from link: {e}")
            return None

    async def _extract_article_from_element(self, article_elem) -> Optional[Dict[str, Any]]:
        """
        从文章元素中提取数据

        Args:
            article_elem: 文章DOM元素

        Returns:
            文章数据字典
        """
        try:
            # 提取标题和URL
            title_link = await article_elem.query_selector("h2 a, h3 a, .wp-block-post-title a")
            if not title_link:
                return None

            url = await title_link.get_attribute("href")
            title = (await title_link.inner_text()).strip()

            if not url or not title:
                return None

            # 提取描述/摘要
            description_elem = await article_elem.query_selector(".wp-block-post-excerpt__excerpt, p")
            description = ""
            if description_elem:
                description = (await description_elem.inner_text()).strip()

            # 提取日期
            date_elem = await article_elem.query_selector(".wp-block-post-date time, time")
            published_at = datetime.now()
            if date_elem:
                date_text = await date_elem.get_attribute("datetime")
                if not date_text:
                    date_text = (await date_elem.inner_text()).strip()
                published_at = self._parse_date(date_text)

            # 提取作者
            author_elems = await article_elem.query_selector_all(".wp-block-post-author__name a, .author a")
            authors = []
            for author_elem in author_elems:
                author_name = (await author_elem.inner_text()).strip()
                if author_name:
                    authors.append(author_name)
            provider = ", ".join(authors) if authors else None

            # 提取标签/分类
            tag_elems = await article_elem.query_selector_all(".wp-block-post-terms__term, .post-categories a, .tags a")
            tags = []
            for tag_elem in tag_elems:
                tag_text = (await tag_elem.inner_text()).strip()
                if tag_text:
                    tags.append(tag_text)

            external_id = self._extract_id_from_url(url)

            return {
                "external_id": external_id,
                "title": title,
                "content": title,  # 暂时使用标题，后续访问详情页替换
                "summary": description if description else None,
                "provider": provider,
                "published_at": published_at,
                "url": url,
                "region": self.region,
                "category": tags[0] if tags else None,  # 第一个标签作为分类
                "language": self.language,
                "tags": tags if tags else None
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
            await asyncio.sleep(2)

            # 提取文章正文内容
            # Ada Lovelace详情页使用.wp-block-post-content或article容器
            paragraphs = await detail_page.query_selector_all(
                '.wp-block-post-content p, article p, .entry-content p'
            )
            content_parts = []

            for para in paragraphs:
                para_text = (await para.inner_text()).strip()
                # 过滤掉非正文内容
                if para_text and len(para_text) > 10:
                    # 排除常见的UI元素
                    if para_text not in ['Share', 'Download', 'Print', 'Subscribe', 'Read more']:
                        # 排除短作者信息行（通常包含逗号且很短）
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

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取文章ID

        Args:
            url: 文章URL，如 /blog/synthetic-data-real-harm/

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
            date_text: 日期文本，如 "2025-09-18" 或 "18 September 2025"

        Returns:
            datetime对象
        """
        try:
            # 尝试ISO格式
            if 'T' in date_text or '-' in date_text[:10]:
                try:
                    return datetime.fromisoformat(date_text.replace('Z', '+00:00'))
                except ValueError:
                    pass

            # 尝试英文格式（多种）
            for fmt in ['%d %B %Y', '%B %d, %Y', '%d %b %Y', '%b %d, %Y', '%Y-%m-%d', '%d/%m/%Y']:
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
        存储到MySQL和ChromaDB（预翻译模式）

        Args:
            items: 文章列表
        """
        # 预翻译阶段：在数据库事务外完成所有翻译
        translated_summaries = {}
        for item in items:
            summary = await self._generate_summary(item.get('summary'), item.get('content', ''))
            translated_summaries[item['url']] = summary

        # 存储阶段：使用翻译结果
        mysql_task = self._store_to_mysql(items, translated_summaries)
        chroma_task = self._store_to_chroma(items, translated_summaries)
        await asyncio.gather(mysql_task, chroma_task, return_exceptions=True)

    async def _store_to_mysql(
        self,
        items: List[Dict[str, Any]],
        translated_summaries: Dict[str, str]
    ) -> None:
        """
        存储到MySQL

        Args:
            items: 文章列表
            translated_summaries: 预翻译的摘要字典
        """
        try:
            with create_session() as db:
                for item in items:
                    summary = translated_summaries.get(item['url'], '')

                    message = AdaLovelaceMessage(
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
                        language=item.get('language'),
                        tags=item.get('tags')
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

    async def _store_to_chroma(
        self,
        items: List[Dict[str, Any]],
        translated_summaries: Dict[str, str]
    ) -> None:
        """
        存储到ChromaDB

        Args:
            items: 文章列表
            translated_summaries: 预翻译的摘要字典
        """
        if not self.chroma_storage or not self.embedding_client:
            return

        try:
            for item in items:
                summary = translated_summaries.get(item['url'], '')
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

        # 3. 外文内容：翻译成中文（全文翻译，不截断）
        if self.translator:
            try:
                translated = await self.translator.translate(
                    source_text,
                    context="Ada Lovelace Institute AI治理研究文章摘要"
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
