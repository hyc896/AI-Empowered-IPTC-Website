# -*- coding: utf-8 -*-

"""
Korea Herald Tech News Collector
Korea Herald科技新闻采集器（韩国科技、半导体、AI领域新闻）

数据来源：
- Business RSS feed: https://www.koreaherald.com/rss/kh_Business

架构特点：
- RSS解析：解析Business feed，通过关键词过滤科技内容
- 预翻译模式：在数据库会话外完成翻译
- 预增强模式：在数据库会话外完成字段增强（region + industry_tags）
- 详情页抓取：RSS提供摘要，需访问详情页获取完整content
"""

import re
import uuid
import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright
from sqlalchemy.exc import IntegrityError
import aiohttp

from backend.database.entities import KoreaHeraldMessage
from backend.database.connection import create_session

try:
    from backend.storage import get_chromadb_storage
    _chroma_available = True
except ImportError:
    _chroma_available = False

try:
    from backend.llm import get_embedding_client, get_translator
    from backend.services import get_field_enricher
    _llm_available = True
except ImportError:
    _llm_available = False

logger = logging.getLogger(__name__)


class KoreaHeraldCollector:
    """Korea Herald科技新闻采集器"""

    # RSS feed URL
    RSS_FEED_URL = "https://www.koreaherald.com/rss/kh_Business"

    # 科技相关关键词（用于过滤Business feed中的科技内容）
    TECH_KEYWORDS = [
        # AI相关
        'ai', 'artificial intelligence', 'machine learning', 'deep learning',
        'neural network', 'chatgpt', 'generative ai', 'llm',
        # 半导体/芯片
        'semiconductor', 'chip', 'chipmaker', 'foundry', 'fab', 'wafer',
        'samsung electronics', 'sk hynix', 'tsmc', 'memory chip', 'dram', 'nand',
        # 科技公司/产品
        'technology', 'tech', 'software', 'hardware', 'computing', 'cloud',
        'data center', 'server', 'processor', 'gpu', 'cpu',
        # 网络安全
        'cybersecurity', 'security', 'hacking', 'breach', 'encryption',
        # 创新/投资
        'innovation', 'startup', 'venture', 'funding', 'investment',
        # 电子/制造
        'electronics', 'manufacturing', 'automation', 'robotics',
        '5g', '6g', 'wireless', 'telecom',
        # 韩国科技巨头
        'naver', 'kakao', 'lg electronics', 'sk telecom'
    ]

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - source_id: 消息源ID（关联message_sources表）
                - region: 地区（KR=Korea 韩国）
                - language: 语言（en）
        """
        self.config = config
        self.interval = config.get('interval', 14400)  # 默认4小时一次
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.source_id = config.get('id', 'auto')
        self.region = config['config'].get('region', 'KR')
        self.language = config['config'].get('language', 'en')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【Korea Herald】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
            self.field_enricher = get_field_enricher()
        else:
            self.embedding_client = None
            self.translator = None
            self.field_enricher = None
            logger.warning("【Korea Herald】LLM服务不可用，将跳过向量化、翻译和字段增强")

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

            logger.info("【Korea Herald】采集器初始化成功")
            return True
        except Exception as e:
            logger.error(f"【Korea Herald】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【Korea Herald】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【Korea Herald】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【Korea Herald】采集失败: {e}", exc_info=True)

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        await self._close_browser()
        logger.info("【Korea Herald】采集器已停止")

    async def _close_browser(self) -> None:
        """关闭浏览器"""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.warning(f"【Korea Herald】关闭浏览器失败: {e}")

    async def _collect_once(self) -> None:
        """
        单次采集（流式处理架构）

        流程（Fail Fast原则）：
        1. 获取MySQL中最新文章URL
        2. 解析RSS feed
        3. 过滤科技相关文章
        4. 分批处理（每批10篇）
        5. 每批：访问详情页 → 翻译 → 存储 → 下一批
        6. 单条失败不影响整体，立即记录错误
        """
        try:
            latest_url = await self._get_latest_stored_url()
            logger.debug(f"【Korea Herald】Latest stored URL: {latest_url}")

            # 解析RSS feed
            articles = await self._parse_rss_feed(latest_url)

            if not articles:
                logger.info("【Korea Herald】无新文章")
                return

            logger.info(f"【Korea Herald】解析到 {len(articles)} 篇科技相关文章")

            # 分批处理（每批10篇，防止并发过载）
            batch_size = 10
            total_stored = 0

            for batch_start in range(0, len(articles), batch_size):
                batch_end = min(batch_start + batch_size, len(articles))
                batch = articles[batch_start:batch_end]

                logger.info(f"【Korea Herald】处理批次 [{batch_start+1}-{batch_end}/{len(articles)}]")

                # 1. 访问详情页（串行，避免反爬虫）
                for idx, item in enumerate(batch, batch_start + 1):
                    try:
                        full_content = await self._fetch_article_content(item['url'])
                        if full_content:
                            item['content'] = full_content
                            logger.debug(f"[{idx}/{len(articles)}] ✓ 详情: {item['url']}")
                        else:
                            logger.debug(f"[{idx}/{len(articles)}] ⚠ 使用RSS摘要: {item['url']}")
                        # 延迟避免反爬虫
                        await asyncio.sleep(1.5)
                    except Exception as e:
                        logger.error(f"[{idx}/{len(articles)}] ✗ 详情页失败: {e}")
                        # Fail Fast：单条失败不影响批次，继续处理

                # 2. 预处理（翻译+字段增强，批内并发）
                await self._preprocess_items(batch)

                # 3. 存储（MySQL + ChromaDB）
                stored_count = await self._store_items(batch)
                total_stored += stored_count

            logger.info(f"【Korea Herald】采集完成，共存储 {total_stored} 条新记录")

            # 更新last_crawled_at
            await self._update_last_crawled()

        except Exception as e:
            logger.error(f"【Korea Herald】单次采集失败: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取数据库中最新的文章URL

        Returns:
            最新文章的URL，如果数据库为空则返回None
        """
        try:
            with create_session() as db:
                latest = db.query(KoreaHeraldMessage).order_by(
                    KoreaHeraldMessage.published_at.desc()
                ).first()
                return latest.url if latest else None
        except Exception as e:
            logger.error(f"【Korea Herald】查询最新URL失败: {e}")
            return None

    async def _parse_rss_feed(self, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        解析RSS feed并过滤科技内容

        Args:
            latest_url: 最新已存储的URL，遇到此URL立即停止

        Returns:
            文章列表
        """
        articles = []

        try:
            # 使用aiohttp获取RSS XML内容（Playwright会返回渲染后的HTML）
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(self.RSS_FEED_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        logger.error(f"【Korea Herald】RSS请求失败: {response.status}")
                        return []

                    rss_content = await response.text()

            # 解析XML
            root = ET.fromstring(rss_content)

            # RSS标准格式：<rss><channel><item>...
            channel = root.find('channel')
            if channel is None:
                logger.error("【Korea Herald】RSS格式错误：未找到channel元素")
                return []

            # 遍历所有item
            items = channel.findall('item')
            logger.info(f"【Korea Herald】RSS中找到 {len(items)} 个item")

            for item in items:
                try:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    description_elem = item.find('description')
                    pub_date_elem = item.find('pubDate')
                    author_elem = item.find('author')
                    category_elem = item.find('category')

                    if not title_elem or not link_elem:
                        continue

                    title = title_elem.text.strip() if title_elem.text else ""
                    link = link_elem.text.strip() if link_elem.text else ""
                    description = description_elem.text.strip() if description_elem and description_elem.text else ""

                    # 去重检查
                    if latest_url and link == latest_url:
                        logger.info(f"【Korea Herald】遇到已存储文章，停止解析: {link}")
                        break

                    # 科技内容过滤
                    if not self._is_tech_related(title, description):
                        logger.debug(f"【Korea Herald】跳过非科技文章: {title[:50]}")
                        continue

                    logger.debug(f"【Korea Herald】匹配到科技文章: {title[:50]}")

                    # 解析发布时间
                    published_at = None
                    if pub_date_elem and pub_date_elem.text:
                        try:
                            # RSS 2.0格式：Mon, 17 Nov 2025 21:44:23 +09:00
                            pub_date_str = pub_date_elem.text.strip()
                            published_at = datetime.strptime(
                                pub_date_str,
                                "%a, %d %b %Y %H:%M:%S %z"
                            )
                        except Exception as e:
                            logger.warning(f"【Korea Herald】解析时间失败: {pub_date_elem.text}, {e}")

                    # 提取external_id（从URL中提取article ID）
                    external_id = self._extract_article_id(link)

                    article_data = {
                        'title': title,
                        'url': link,
                        'content': description,  # RSS中的description作为初始content
                        'provider': author_elem.text.strip() if author_elem and author_elem.text else "The Korea Herald",
                        'published_at': published_at,
                        'external_id': external_id,
                        'category': category_elem.text.strip() if category_elem and category_elem.text else "Business"
                    }

                    articles.append(article_data)

                except Exception as e:
                    logger.error(f"【Korea Herald】解析RSS item失败: {e}")
                    continue

            logger.info(f"【Korea Herald】RSS解析完成，筛选出 {len(articles)} 篇科技文章")

        except Exception as e:
            logger.error(f"【Korea Herald】RSS解析失败: {e}", exc_info=True)

        return articles

    def _is_tech_related(self, title: str, description: str) -> bool:
        """
        判断文章是否与科技相关

        Args:
            title: 文章标题
            description: 文章摘要

        Returns:
            是否科技相关
        """
        text = (title + " " + description).lower()

        for keyword in self.TECH_KEYWORDS:
            if keyword.lower() in text:
                return True

        return False

    def _extract_article_id(self, url: str) -> str:
        """
        从URL中提取article ID

        Args:
            url: 文章URL（如 https://www.koreaherald.com/article/10617883）

        Returns:
            article ID
        """
        match = re.search(r'/article/(\d+)', url)
        if match:
            return match.group(1)
        return url  # 如果提取失败，使用完整URL作为fallback

    async def _fetch_article_content(self, url: str) -> Optional[str]:
        """
        访问详情页获取完整正文内容

        Args:
            url: 文章URL

        Returns:
            完整正文，失败返回None
        """
        page: Optional[Page] = None

        try:
            page = await self._browser.new_page()
            await page.goto(url, timeout=30000, wait_until='networkidle')

            # 等待内容加载
            await page.wait_for_selector('h1', timeout=10000)

            # 提取所有段落（<p>标签）
            paragraphs = await page.query_selector_all('p')

            content_parts = []
            for p in paragraphs:
                text = await p.inner_text()
                text = text.strip()

                # 过滤非内容段落
                if not text or len(text) < 20:
                    continue

                # 过滤常见的非内容文本
                if any(skip in text.lower() for skip in [
                    'share this article',
                    'subscribe',
                    'newsletter',
                    'most read',
                    'related articles',
                    'advertisement'
                ]):
                    continue

                content_parts.append(text)

            if content_parts:
                full_content = '\n\n'.join(content_parts)
                return full_content

            return None

        except Exception as e:
            logger.error(f"【Korea Herald】获取详情页失败 {url}: {e}")
            return None
        finally:
            if page:
                await page.close()

    async def _preprocess_items(self, items: List[Dict[str, Any]]) -> None:
        """
        预处理文章列表（翻译 + 字段增强）

        在数据库会话外执行所有异步操作，遵循异步编程铁律

        Args:
            items: 文章列表（会直接修改item添加translated_summary等字段）
        """
        if not self.translator or not self.field_enricher:
            logger.warning("【Korea Herald】翻译或字段增强服务不可用，跳过预处理")
            return

        # 1. 批量翻译summary（并发）
        translation_tasks = []
        for item in items:
            # 使用content作为翻译源（RSS description或详情页正文）
            content = item.get('content', '')
            if content:
                task = self.translator.translate(
                    content,
                    context="Korea Herald科技新闻摘要"
                )
                translation_tasks.append((item, task))

        # 等待所有翻译完成
        for item, task in translation_tasks:
            try:
                translated = await task
                item['translated_summary'] = translated
            except Exception as e:
                logger.error(f"【Korea Herald】翻译失败 {item.get('url')}: {e}")
                # 降级：使用原文截断
                item['translated_summary'] = item.get('content', '')[:1000]

        # 2. 批量字段增强（并发）
        enrichment_tasks = []
        for item in items:
            title = item.get('title', '')
            content = item.get('content', '')
            if title or content:
                task = self.field_enricher.enrich_fields(title, content)
                enrichment_tasks.append((item, task))

        # 等待所有字段增强完成
        for item, task in enrichment_tasks:
            try:
                enriched = await task
                item['enriched_region'] = enriched.get('region', '韩国')
                item['enriched_industry_tags'] = enriched.get('industry_tags', '')
                item['enriched_ai_tag'] = enriched.get('ai_tag', '')
            except Exception as e:
                logger.error(f"【Korea Herald】字段增强失败 {item.get('url')}: {e}")
                # 降级：使用默认值
                item['enriched_region'] = '韩国'
                item['enriched_industry_tags'] = ''
                item['enriched_ai_tag'] = ''

    async def _store_items(self, items: List[Dict[str, Any]]) -> int:
        """
        存储文章到MySQL和ChromaDB

        Args:
            items: 预处理后的文章列表

        Returns:
            成功存储的数量
        """
        stored_count = 0

        # 存储到MySQL
        try:
            with create_session() as db:
                for item in items:
                    try:
                        message = KoreaHeraldMessage(
                            id=str(uuid.uuid4()),
                            source_id=self.source_id,
                            external_id=item.get('external_id'),
                            title=item['title'],
                            content=item.get('content', ''),
                            summary=item.get('translated_summary', ''),
                            provider=item.get('provider', 'The Korea Herald'),
                            published_at=item.get('published_at'),
                            crawled_at=datetime.now(),
                            url=item['url'],
                            region=item.get('enriched_region', '韩国'),
                            industry_tags=item.get('enriched_industry_tags', ''),
                            ai_tag=item.get('enriched_ai_tag', ''),
                            category=item.get('category', 'Business'),
                            language=self.language
                        )

                        db.add(message)
                        db.commit()
                        stored_count += 1

                        # 存储到ChromaDB
                        if self.chroma_storage and self.embedding_client:
                            await self._store_to_chromadb(message)

                    except IntegrityError:
                        db.rollback()
                        logger.debug(f"【Korea Herald】重复记录已跳过: {item['url']}")
                    except Exception as e:
                        db.rollback()
                        logger.error(f"【Korea Herald】存储失败 {item.get('url')}: {e}")

        except Exception as e:
            logger.error(f"【Korea Herald】批量存储失败: {e}", exc_info=True)

        return stored_count

    async def _store_to_chromadb(self, message: KoreaHeraldMessage) -> None:
        """
        存储消息到ChromaDB

        Args:
            message: 消息对象
        """
        try:
            if not self.chroma_storage or not self.embedding_client:
                return

            # 生成embedding
            text_for_embedding = f"{message.title}\n\n{message.summary or message.content[:500]}"
            embedding = await self.embedding_client.get_embedding(text_for_embedding)

            # 存储到ChromaDB
            self.chroma_storage.upsert(
                collection_name=self.chroma_collection,
                ids=[message.external_id or message.id],
                documents=[text_for_embedding],
                embeddings=[embedding],
                metadatas=[{
                    'id': message.id,
                    'source_id': message.source_id,
                    'title': message.title,
                    'summary': message.summary or '',
                    'published_at': message.published_at.isoformat() if message.published_at else '',
                    'url': message.url,
                    'region': message.region or '',
                    'category': message.category or ''
                }]
            )

        except Exception as e:
            logger.error(f"【Korea Herald】ChromaDB存储失败 {message.url}: {e}")

    async def _update_last_crawled(self) -> None:
        """更新消息源的last_crawled_at时间戳"""
        try:
            from backend.database.entities import MessageSource

            with create_session() as db:
                source = db.query(MessageSource).filter(
                    MessageSource.id == self.source_id
                ).first()

                if source:
                    source.last_crawled_at = datetime.now()
                    db.commit()

        except Exception as e:
            logger.error(f"【Korea Herald】更新last_crawled_at失败: {e}")
