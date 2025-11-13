# -*- coding: utf-8 -*-

"""
Policy Innovation Lab, Stellenbosch University Collector
斯坦陵布什大学政策创新实验室采集器
"""

import re
import json
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright
from sqlalchemy.exc import IntegrityError

from backend.database.entities import StellenboschMessage
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


class StellenboschCollector:
    """斯坦陵布什大学政策创新实验室采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - url: 新闻列表页URL
                - source_id: 消息源ID（关联message_sources表）
                - region: 地区（ZA=South Africa）
                - language: 语言（en）
        """
        self.config = config
        self.interval = config.get('interval', 86400)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.url = config['config'].get('url', 'https://policyinnovationlab.sun.ac.za/news/')
        self.source_id = config.get('id', 'auto')
        self.region = config['config'].get('region', 'ZA')
        self.language = config['config'].get('language', 'en')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【Stellenbosch】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【Stellenbosch】LLM服务不可用，将跳过向量化和翻译")

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

            logger.info(f"【Stellenbosch】采集器初始化成功: {self.url}")
            return True
        except Exception as e:
            logger.error(f"【Stellenbosch】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【Stellenbosch】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【Stellenbosch】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【Stellenbosch】采集失败: {e}")

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        await self._close_browser()
        logger.info("【Stellenbosch】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新文章URL
        2. Playwright爬取列表页
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
                logger.info(f"【Stellenbosch】开始访问 {len(new_items)} 篇文章的详情页...")
                for idx, item in enumerate(new_items, 1):
                    try:
                        full_content = await self._fetch_article_content(item['url'])
                        if full_content:
                            item['content'] = full_content
                            logger.debug(f"[{idx}/{len(new_items)}] ✓ 获取完整内容: {item['url']}")
                        else:
                            logger.debug(f"[{idx}/{len(new_items)}] ⚠ 保持使用标题: {item['url']}")

                        # 延迟1秒避免频繁请求
                        if idx < len(new_items):
                            await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"[{idx}/{len(new_items)}] ✗ 详情页访问失败: {e}")

                await self._store_items(new_items)
                logger.info(f"【Stellenbosch】采集到 {len(new_items)} 篇新文章")
            else:
                logger.debug("【Stellenbosch】所有文章已存在，无新数据")

        except Exception as e:
            logger.error(f"【Stellenbosch】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新文章的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(StellenboschMessage).filter(
                    StellenboschMessage.source_id == self.source_id,
                    StellenboschMessage.url.isnot(None)
                ).order_by(
                    StellenboschMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL: {e}")
            return None

    async def _scrape_articles_list(self, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        Playwright爬取列表页，提取文章列表

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

                await page.goto(self.url, wait_until="networkidle", timeout=90000)
                await asyncio.sleep(5)
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"【Stellenbosch】第 {attempt + 1} 次尝试失败: {e}，{retry_delay}秒后重试...")
                    if page:
                        await page.close()
                        page = None
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【Stellenbosch】所有重试均失败: {e}", exc_info=True)
                    if page:
                        await page.close()
                    return []

        if not page:
            return []

        try:
            # 等待页面内容加载（尝试多个可能的选择器）
            articles_selector = ".eg-grid-item"
            try:
                await page.wait_for_selector(articles_selector, timeout=20000)
            except Exception:
                # 尝试备用选择器
                logger.warning("【Stellenbosch】主选择器未找到，尝试备用选择器...")
                articles_selector = "article, .post, .entry, [class*='item']"
                await page.wait_for_selector(articles_selector, timeout=20000)

            # 持续滚动加载更多内容
            articles_list = []
            load_more_attempts = 0
            max_load_attempts = 30
            consecutive_no_new = 0
            max_consecutive_no_new = 3

            while load_more_attempts < max_load_attempts:
                # 获取当前所有文章元素
                article_elements = await page.query_selector_all(articles_selector)
                current_count = len(article_elements)
                logger.debug(f"当前页面文章数量: {current_count}")

                # 从当前位置开始提取新文章
                start_index = len(articles_list)
                for idx in range(start_index, current_count):
                    article_elem = article_elements[idx]
                    article_data = await self._extract_article_from_element(article_elem)

                    if not article_data:
                        continue

                    article_url = article_data.get('url')
                    if not article_url:
                        continue

                    # 遇到最新已存储URL，停止采集
                    if latest_url and article_url == latest_url:
                        logger.debug(f"Reached latest stored URL ({latest_url}), stopping")
                        return articles_list

                    articles_list.append(article_data)

                # 检查是否有新文章
                if len(articles_list) == start_index:
                    consecutive_no_new += 1
                    logger.debug(f"本次滚动未发现新内容 ({consecutive_no_new}/{max_consecutive_no_new})")
                    if consecutive_no_new >= max_consecutive_no_new:
                        logger.debug("连续3次滚动无新内容，停止加载")
                        break
                else:
                    consecutive_no_new = 0

                # 滚动到页面底部触发加载
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(3)

                load_more_attempts += 1

            logger.info(f"【Stellenbosch】共提取 {len(articles_list)} 篇文章")
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
            article_elem: 文章DOM元素

        Returns:
            文章数据字典
        """
        try:
            # 提取标题和URL
            title_link_elem = await article_elem.query_selector("a[href*='policyinnovationlab.sun.ac.za']")
            if not title_link_elem:
                return None

            url = await title_link_elem.get_attribute("href")

            # 提取标题（可能在多个位置）
            title_elem = await article_elem.query_selector("h2, h3, .title, .entry-title")
            if not title_elem:
                return None

            title = (await title_elem.inner_text()).strip()

            if not url or not title:
                return None

            # URL规范化
            if not url.startswith('http'):
                url = f"https://policyinnovationlab.sun.ac.za{url}"

            external_id = self._extract_id_from_url(url)

            return {
                "external_id": external_id,
                "title": title,
                "content": title,  # 初始值，后续从详情页更新
                "url": url,
                "region": self.region,
                "language": self.language,
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

            # 尝试提取JSON-LD结构化数据
            json_ld_content = await self._extract_json_ld_data(detail_page)

            # 提取正文段落
            paragraphs = await detail_page.query_selector_all('article p, .post-content p, .entry-content p, .content p')
            content_parts = []

            for para in paragraphs:
                para_text = (await para.inner_text()).strip()
                # 过滤掉非正文内容
                if para_text and len(para_text) > 10:
                    # 排除分享按钮、作者信息等
                    if not any(keyword in para_text.lower() for keyword in ['share', 'facebook', 'twitter', 'linkedin', 'email']):
                        # 排除短作者信息行
                        if len(para_text) > 30 or ',' not in para_text:
                            content_parts.append(para_text)

            full_content = '\n\n'.join(content_parts)

            # 如果常规提取失败，尝试从JSON-LD获取
            if not full_content and json_ld_content:
                full_content = json_ld_content

            return full_content if full_content else None

        except Exception as e:
            logger.error(f"获取文章详情失败 {article_url}: {e}")
            return None
        finally:
            if detail_page:
                await detail_page.close()

    async def _extract_json_ld_data(self, page: Page) -> Optional[str]:
        """
        提取JSON-LD结构化数据

        Args:
            page: Playwright页面对象

        Returns:
            提取的内容或None
        """
        try:
            json_ld_script = await page.query_selector('script[type="application/ld+json"]')
            if not json_ld_script:
                return None

            json_text = await json_ld_script.inner_text()
            data = json.loads(json_text)

            # 提取文章正文（如果存在）
            if isinstance(data, dict):
                article_body = data.get('articleBody', '')
                if article_body:
                    return article_body

            return None
        except Exception as e:
            logger.debug(f"JSON-LD提取失败: {e}")
            return None

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取文章ID

        Args:
            url: 文章URL，如 https://policyinnovationlab.sun.ac.za/goalkeepers-exploring-gendered-leadership/

        Returns:
            文章路径slug作为ID
        """
        try:
            match = re.search(r'/([^/]+)/?$', url)
            return match.group(1) if match else None
        except Exception:
            return None

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
        并发存储到MySQL和ChromaDB（预翻译模式）

        Args:
            items: 文章列表
        """
        # 预先生成所有summary（在数据库会话外）
        summaries = []
        for item in items:
            summary = await self._generate_summary(item.get('summary'), item.get('content', ''))
            summaries.append(summary)

        # 批量存储
        mysql_task = self._store_to_mysql(items, summaries)
        chroma_task = self._store_to_chroma(items, summaries)
        await asyncio.gather(mysql_task, chroma_task, return_exceptions=True)

    async def _store_to_mysql(self, items: List[Dict[str, Any]], summaries: List[str]) -> None:
        """
        存储到MySQL

        Args:
            items: 文章列表
            summaries: 预生成的摘要列表
        """
        try:
            with create_session() as db:
                for idx, item in enumerate(items):
                    summary = summaries[idx]

                    message = StellenboschMessage(
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
                        word_count=item.get('word_count'),
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
            summaries: 预生成的摘要列表
        """
        if not self.chroma_storage or not self.embedding_client:
            return

        try:
            for idx, item in enumerate(items):
                summary = summaries[idx]
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
                # 全文翻译（不截断）
                translated = await self.translator.translate(
                    source_text,
                    context="斯坦陵布什大学政策创新实验室新闻文章"
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
