# -*- coding: utf-8 -*-

"""
HSE University AI Research Centre Collector
俄罗斯高等经济学院AI研究中心新闻采集器
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
import aiohttp
from sqlalchemy.exc import IntegrityError

from backend.database.entities import HSEAIMessage
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


class HSEAICollector:
    """HSE AI研究中心新闻采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - url: HSE AI Centre新闻列表页URL
                - source_id: 消息源ID（关联message_sources表）
                - region: 地区（RU=Russia）
                - language: 语言（en）
        """
        self.config = config
        self.interval = config.get('interval', 86400)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.base_url = config['config'].get('url', 'https://cs.hse.ru/en/aicenter/news/')
        self.source_id = config.get('id', 'auto')
        self.region = config['config'].get('region', 'RU')
        self.language = config['config'].get('language', 'en')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【HSE AI】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【HSE AI】LLM服务不可用，将跳过向量化和翻译")

        self._running = False
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> bool:
        """
        初始化采集器（创建HTTP会话）

        Returns:
            是否初始化成功
        """
        try:
            self._session = aiohttp.ClientSession(
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                },
                timeout=aiohttp.ClientTimeout(total=60)
            )

            if self.chroma_storage:
                self.chroma_storage.create_collection(
                    collection_name=self.chroma_collection
                )

            logger.info(f"【HSE AI】采集器初始化成功: {self.base_url}")
            return True
        except Exception as e:
            logger.error(f"【HSE AI】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【HSE AI】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【HSE AI】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【HSE AI】采集失败: {e}", exc_info=True)

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        if self._session:
            await self._session.close()
        logger.info("【HSE AI】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新文章URL
        2. 抓取新闻列表页（支持分页）
        3. 过滤已存在URL
        4. 访问详情页获取完整内容
        5. 预翻译所有摘要（在session外）
        6. 并发存储到MySQL + ChromaDB
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
                logger.info(f"【HSE AI】开始访问 {len(new_items)} 篇文章的详情页...")
                for idx, item in enumerate(new_items, 1):
                    try:
                        full_content = await self._fetch_article_content(item['url'])
                        if full_content:
                            item['content'] = full_content
                            logger.debug(f"[{idx}/{len(new_items)}] ✓ 获取完整内容: {item['url']}")
                        else:
                            logger.debug(f"[{idx}/{len(new_items)}] ⚠ 保持使用摘要: {item['url']}")

                        # 添加延迟避免触发反爬虫
                        await asyncio.sleep(1.5)
                    except Exception as e:
                        logger.error(f"[{idx}/{len(new_items)}] ✗ 详情页访问失败: {e}")

                # 预翻译策略：在数据库session外完成所有翻译
                logger.info(f"【HSE AI】预翻译 {len(new_items)} 篇文章摘要...")
                translated_summaries = []
                for idx, item in enumerate(new_items, 1):
                    summary = await self._generate_summary(item.get('summary'), item.get('content', ''))
                    translated_summaries.append(summary)
                    logger.debug(f"[{idx}/{len(new_items)}] 翻译完成")

                # 将翻译结果存入items
                for item, summary in zip(new_items, translated_summaries):
                    item['translated_summary'] = summary

                await self._store_items(new_items)
                logger.info(f"【HSE AI】采集到 {len(new_items)} 篇新文章")
            else:
                logger.debug("【HSE AI】所有文章已存在，无新数据")

        except Exception as e:
            logger.error(f"【HSE AI】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新文章的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(HSEAIMessage).filter(
                    HSEAIMessage.source_id == self.source_id,
                    HSEAIMessage.url.isnot(None)
                ).order_by(
                    HSEAIMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL: {e}")
            return None

    async def _scrape_articles_list(self, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        抓取新闻列表页（支持分页）

        Args:
            latest_url: 最新已存储的URL，遇到此URL立即停止

        Returns:
            文章列表
        """
        all_articles = []
        page_num = 1
        max_pages = 10  # 安全上限：最多抓取10页

        while page_num <= max_pages:
            try:
                # 构建分页URL
                if page_num == 1:
                    page_url = self.base_url
                else:
                    page_url = f"{self.base_url}page{page_num}.html"

                logger.debug(f"正在抓取第 {page_num} 页: {page_url}")

                articles, should_stop = await self._scrape_single_page(page_url, latest_url)

                if not articles:
                    logger.debug(f"第 {page_num} 页无内容，停止翻页")
                    break

                all_articles.extend(articles)

                if should_stop:
                    logger.debug(f"在第 {page_num} 页遇到已存在URL，停止翻页")
                    break

                page_num += 1
                await asyncio.sleep(2)  # 翻页延迟

            except Exception as e:
                logger.error(f"抓取第 {page_num} 页失败: {e}")
                break

        logger.info(f"【HSE AI】共抓取 {len(all_articles)} 篇文章（{page_num} 页）")
        return all_articles

    async def _scrape_single_page(self, page_url: str, latest_url: Optional[str]) -> tuple[List[Dict[str, Any]], bool]:
        """
        抓取单个列表页

        Args:
            page_url: 页面URL
            latest_url: 最新已存储的URL

        Returns:
            (文章列表, 是否应该停止翻页)
        """
        max_retries = 3
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                async with self._session.get(page_url) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status}: {page_url}")
                        return [], False

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # 新闻列表容器（根据WebFetch分析，需要实际测试定位）
                    # HSE网站结构：每条新闻包含标题链接、日期、摘要
                    articles_list = []
                    should_stop = False

                    # 尝试多种可能的选择器
                    news_items = soup.select('article, .news-item, .post, div[class*="news"], div[class*="item"]')

                    if not news_items:
                        # 备用策略：查找所有包含新闻链接的容器
                        news_items = soup.find_all('a', href=re.compile(r'/news/.+/\d+\.html'))

                    logger.debug(f"Found {len(news_items)} potential news items")

                    for item in news_items:
                        article_data = self._extract_article_from_element(item, soup)

                        if not article_data:
                            continue

                        article_url = article_data.get('url')
                        if not article_url:
                            continue

                        # 遇到已存在URL，停止采集
                        if latest_url and article_url == latest_url:
                            logger.debug(f"Reached latest stored URL ({latest_url}), stopping")
                            should_stop = True
                            break

                        articles_list.append(article_data)

                    return articles_list, should_stop

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"第 {attempt + 1} 次尝试失败: {e}，{retry_delay}秒后重试...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"所有重试均失败: {e}", exc_info=True)
                    return [], False

        return [], False

    def _extract_article_from_element(self, element, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        从HTML元素中提取文章数据

        Args:
            element: BeautifulSoup元素
            soup: 完整页面的BeautifulSoup对象

        Returns:
            文章数据字典
        """
        try:
            # 提取标题和URL
            if element.name == 'a':
                title_link = element
            else:
                title_link = element.find('a', href=re.compile(r'/news/.+/\d+\.html'))

            if not title_link:
                return None

            url = title_link.get('href', '')
            title = title_link.get_text(strip=True)

            if not url or not title:
                return None

            # 补全相对URL（避免重复拼接）
            if not url.startswith('http'):
                if url.startswith('/'):
                    url = f"https://www.hse.ru{url}"
                else:
                    url = f"https://www.hse.ru/en/{url}"

            # 提取日期（多种模式）
            published_at = datetime.now()
            date_patterns = [
                r'(\w+ \d{1,2},? \d{4})',  # October 27, 2025
                r'(\d{4}-\d{2}-\d{2})',     # 2025-10-27
                r'(\w+ \d{1,2})',           # October 27
            ]

            # 在父容器中查找日期
            parent = element.parent if element.parent else element
            parent_text = parent.get_text()

            for pattern in date_patterns:
                match = re.search(pattern, parent_text)
                if match:
                    date_text = match.group(1)
                    published_at = self._parse_date(date_text)
                    break

            # 提取摘要（在同一容器内的段落文本）
            summary = ""
            if element.name != 'a':
                paragraphs = element.find_all('p')
                if paragraphs:
                    summary = ' '.join([p.get_text(strip=True) for p in paragraphs[:2]])

            # 提取分类标签
            tags = []
            tag_elements = element.find_all('a', href=re.compile(r'/tags/|/keywords/'))
            for tag_elem in tag_elements:
                tag_text = tag_elem.get_text(strip=True)
                if tag_text:
                    tags.append(tag_text)

            # 从URL提取ID
            external_id = self._extract_id_from_url(url)

            return {
                "external_id": external_id,
                "title": title,
                "content": summary or title,  # 初始使用摘要，后续访问详情页
                "summary": summary,
                "provider": None,  # 详情页提取
                "published_at": published_at,
                "url": url,
                "region": self.region,
                "category": None,
                "language": self.language,
                "tags": tags if tags else None
            }
        except Exception as e:
            logger.error(f"Failed to extract article from element: {e}")
            return None

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取文章ID

        Args:
            url: 文章URL，如 https://www.hse.ru/en/news/research/1039162800.html

        Returns:
            文章数字ID
        """
        try:
            match = re.search(r'/(\d+)\.html', url)
            return match.group(1) if match else None
        except Exception:
            return None

    def _parse_date(self, date_text: str) -> datetime:
        """
        解析日期文本

        Args:
            date_text: 日期文本，如 "October 27, 2025" 或 "August 05"

        Returns:
            datetime对象
        """
        try:
            # 尝试多种日期格式
            for fmt in ['%B %d, %Y', '%b %d, %Y', '%Y-%m-%d', '%B %d', '%b %d']:
                try:
                    parsed_date = datetime.strptime(date_text.strip(), fmt)
                    # 如果只有月日，补充年份
                    if fmt in ['%B %d', '%b %d']:
                        parsed_date = parsed_date.replace(year=datetime.now().year)
                    return parsed_date
                except ValueError:
                    continue

            logger.warning(f"Failed to parse date text '{date_text}'")
            return datetime.now()
        except Exception as e:
            logger.error(f"Failed to parse date text '{date_text}': {e}")
            return datetime.now()

    async def _fetch_article_content(self, article_url: str) -> Optional[str]:
        """
        访问文章详情页，获取完整内容

        Args:
            article_url: 文章URL

        Returns:
            完整的文章内容
        """
        try:
            async with self._session.get(article_url) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status}: {article_url}")
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # 提取正文内容（尝试多个可能的容器）
                content_selectors = [
                    'article',
                    '.post-content',
                    '.entry-content',
                    '.content-wrapper',
                    'div[class*="content"]',
                    '.news-content',
                ]

                content_parts = []

                for selector in content_selectors:
                    container = soup.select_one(selector)
                    if container:
                        paragraphs = container.find_all('p')
                        for para in paragraphs:
                            para_text = para.get_text(strip=True)
                            # 过滤掉非正文内容
                            if para_text and len(para_text) > 30:
                                # 排除作者信息、分享按钮等
                                if not any(word in para_text for word in ['Share', 'Download', 'Print', 'Subscribe']):
                                    content_parts.append(para_text)

                        if content_parts:
                            break

                full_content = '\n\n'.join(content_parts)
                return full_content if full_content else None

        except Exception as e:
            logger.error(f"获取文章详情失败 {article_url}: {e}")
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
        并发存储到MySQL和ChromaDB

        Args:
            items: 文章列表（已包含translated_summary）
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
                    summary = item.get('translated_summary', '')

                    message = HSEAIMessage(
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
                        tags=item.get('tags'),
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
                summary = item.get('translated_summary', '')
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

        # 3. 外文内容：翻译成中文（不限制长度，信任translator）
        if self.translator:
            try:
                translated = await self.translator.translate(
                    source_text,
                    context="HSE AI研究中心新闻报道"
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
