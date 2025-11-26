# -*- coding: utf-8 -*-

"""
BetaKit Canadian Tech News Collector
BetaKit加拿大科技新闻与创业生态采集器

数据来源：
- RSS Feed: https://betakit.com/feed/
- AI标签: https://betakit.com/tag/artificial-intelligence/feed/
- Machine Learning标签: https://betakit.com/tag/machine-learning/feed/
- Funding标签: https://betakit.com/tag/funding/feed/

架构特点：
- RSS feed采集：无需Playwright，直接解析XML
- 预翻译模式：在数据库会话外完成翻译
- 预增强模式：在数据库会话外完成字段增强（region + industry_tags + ai_tag）
- HTML清理：从content:encoded提取纯文本
- 多标签采集：支持采集多个主题标签的内容
"""

import re
import uuid
import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, List, Optional
from html import unescape
import aiohttp
import requests
from sqlalchemy.exc import IntegrityError

from backend.database.entities import BetaKitMessage
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

try:
    from backend.services import get_field_enricher
    _field_enricher_available = True
except ImportError:
    _field_enricher_available = False

logger = logging.getLogger(__name__)


class BetaKitCollector:
    """BetaKit加拿大科技新闻采集器"""

    # 支持的RSS Feeds配置
    RSS_FEEDS = {
        'ai': {
            'name': 'Artificial Intelligence',
            'url': 'https://betakit.com/tag/artificial-intelligence/feed/',
            'display': 'AI'
        },
        'machine-learning': {
            'name': 'Machine Learning',
            'url': 'https://betakit.com/tag/machine-learning/feed/',
            'display': 'Machine Learning'
        },
        'funding': {
            'name': 'Funding',
            'url': 'https://betakit.com/tag/funding/feed/',
            'display': 'Funding'
        },
        'startups': {
            'name': 'Canadian Startup News',
            'url': 'https://betakit.com/category/canadian-startup-news/feed/',
            'display': 'Startups'
        }
    }

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - id: 消息源ID
                - config: 详细配置
                  - interval: 采集间隔（秒）
                  - mysql_table: MySQL表名
                  - chroma_collection: ChromaDB collection名称
                  - feeds: 要采集的RSS feeds列表（默认全部）
                  - region: 地区（默认"加拿大"）
                  - language: 语言（en）
        """
        self.source_id = config['id']
        self.config = config['config']
        self.interval = self.config.get('interval', 86400)  # 默认每天一次
        self.mysql_table = self.config['mysql_table']
        self.chroma_collection = self.config['chroma_collection']
        self.region = self.config.get('region', '加拿大')
        self.language = self.config.get('language', 'en')

        # 要采集的RSS feeds（默认全部）
        self.enabled_feeds = self.config.get('feeds', ['ai', 'machine-learning', 'funding', 'startups'])

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【BetaKit】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【BetaKit】LLM服务不可用，将跳过向量化和翻译")

        if _field_enricher_available:
            self.field_enricher = get_field_enricher()
        else:
            self.field_enricher = None
            logger.warning("【BetaKit】FieldEnricher不可用，将跳过字段增强")

        self._running = False
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> bool:
        """
        初始化采集器（创建HTTP session）

        Returns:
            是否初始化成功
        """
        try:
            # 创建HTTP session with proper headers and timeout
            timeout = aiohttp.ClientTimeout(total=60, connect=30, sock_read=30)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, ttl_dns_cache=300)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                connector=connector
            )

            if self.chroma_storage:
                self.chroma_storage.create_collection(
                    collection_name=self.chroma_collection
                )

            logger.info(f"【BetaKit】采集器初始化成功（feeds: {', '.join(self.enabled_feeds)}）")
            return True
        except Exception as e:
            logger.error(f"【BetaKit】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【BetaKit】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【BetaKit】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【BetaKit】采集失败: {e}", exc_info=True)

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        if self._session:
            await self._session.close()
        logger.info("【BetaKit】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 遍历所有RSS feeds
        2. 获取MySQL中最新文章URL
        3. 解析RSS XML
        4. 过滤已存在URL
        5. 清理HTML提取纯文本
        6. 预翻译和字段增强（session外）
        7. 并发存储到MySQL + ChromaDB
        """
        total_new_articles = 0

        for feed_key in self.enabled_feeds:
            if feed_key not in self.RSS_FEEDS:
                logger.warning(f"【BetaKit】未知的feed: {feed_key}")
                continue

            feed_config = self.RSS_FEEDS[feed_key]
            feed_name = feed_config['display']
            feed_url = feed_config['url']

            try:
                logger.info(f"【BetaKit】开始采集feed: {feed_name}")

                latest_url = await self._get_latest_stored_url(feed_key)
                logger.debug(f"Latest stored URL for {feed_name}: {latest_url}")

                articles_list = await self._parse_rss_feed(feed_url, feed_key, latest_url)

                if not articles_list:
                    logger.debug(f"【{feed_name}】无新文章")
                    continue

                logger.info(f"【{feed_name}】发现 {len(articles_list)} 篇新文章")

                # 预处理：翻译 + 字段增强（在session外）
                await self._preprocess_items(articles_list)

                # 存储
                await self._store_items(articles_list)
                total_new_articles += len(articles_list)
                logger.info(f"【{feed_name}】成功采集 {len(articles_list)} 篇新文章")

                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"【BetaKit】Feed {feed_name} 采集错误: {e}", exc_info=True)

        if total_new_articles > 0:
            logger.info(f"【BetaKit】本次采集共获取 {total_new_articles} 篇新文章")
        else:
            logger.info(f"【BetaKit】本次采集无新文章")

    async def _get_latest_stored_url(self, feed_category: str) -> Optional[str]:
        """
        获取MySQL中指定feed分类最新文章的URL（使用ORM）

        Args:
            feed_category: feed分类标识

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(BetaKitMessage).filter(
                    BetaKitMessage.source_id == self.source_id,
                    BetaKitMessage.category == feed_category,
                    BetaKitMessage.url.isnot(None)
                ).order_by(
                    BetaKitMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL for {feed_category}: {e}")
            return None

    async def _parse_rss_feed(
        self,
        feed_url: str,
        feed_category: str,
        latest_url: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        解析RSS feed XML

        Args:
            feed_url: RSS feed URL
            feed_category: feed分类标识
            latest_url: 最新已存储的URL，遇到此URL立即停止

        Returns:
            文章列表
        """
        try:
            # 使用requests代替aiohttp（Windows环境下aiohttp连接问题的workaround）
            def fetch_rss():
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                }
                response = requests.get(feed_url, headers=headers, timeout=30)
                return response.status_code, response.text

            status_code, xml_content = await asyncio.to_thread(fetch_rss)

            if status_code != 200:
                logger.error(f"Failed to fetch RSS feed {feed_url}: HTTP {status_code}")
                return []

            root = ET.fromstring(xml_content)

            # 查找所有<item>元素
            items = root.findall('.//item')
            logger.info(f"【{feed_category}】RSS feed包含 {len(items)} 个条目")

            articles = []
            for idx, item_elem in enumerate(items, 1):
                article_data = self._extract_article_from_item(item_elem, feed_category)
                if article_data:
                    # 遇到已存在URL立即停止（不包含该URL）
                    if latest_url and article_data.get('url') == latest_url:
                        logger.debug(f"【{feed_category}】遇到已存在URL，停止解析")
                        break

                    articles.append(article_data)
                else:
                    logger.debug(f"【{feed_category}】Item {idx} extraction failed (returned None)")

            logger.debug(f"【{feed_category}】成功提取 {len(articles)} 篇新文章")
            return articles

        except Exception as e:
            logger.error(f"Failed to parse RSS feed {feed_url}: {e}", exc_info=True)
            return []

    def _extract_article_from_item(self, item_elem, feed_category: str) -> Optional[Dict[str, Any]]:
        """
        从RSS <item>元素提取文章数据

        Args:
            item_elem: <item> XML元素
            feed_category: feed分类标识

        Returns:
            文章数据字典
        """
        try:
            # 提取基本字段
            title_elem = item_elem.find('title')
            link_elem = item_elem.find('link')
            guid_elem = item_elem.find('guid')

            # 必须使用 is None 检查，因为ElementTree.Element在boolean上下文中可能为False
            if title_elem is None or link_elem is None:
                logger.debug(f"【{feed_category}】缺少title或link元素")
                return None

            title = title_elem.text.strip() if title_elem.text else None
            url = link_elem.text.strip() if link_elem.text else None

            if not title or not url:
                logger.debug(f"【{feed_category}】title或url为空")
                return None

            # 提取external_id（从guid提取post ID）
            external_id = None
            if guid_elem is not None and guid_elem.text:
                # guid格式：https://betakit.com/?p=396759
                match = re.search(r'\?p=(\d+)', guid_elem.text)
                if match:
                    external_id = match.group(1)

            if not external_id:
                # 从URL提取slug作为fallback
                external_id = self._extract_slug_from_url(url)

            # 提取作者
            creator_elem = item_elem.find('.//{http://purl.org/dc/elements/1.1/}creator')
            author = None
            if creator_elem is not None and creator_elem.text:
                author = creator_elem.text.strip()

            # 提取发布时间
            pubdate_elem = item_elem.find('pubDate')
            published_at = datetime.now()
            if pubdate_elem is not None and pubdate_elem.text:
                try:
                    # RFC 2822格式：Mon, 17 Nov 2025 12:00:00 +0000
                    from email.utils import parsedate_to_datetime
                    published_at = parsedate_to_datetime(pubdate_elem.text)
                except Exception as e:
                    logger.warning(f"Failed to parse pubDate: {e}")

            # 提取分类标签
            categories = []
            for cat_elem in item_elem.findall('category'):
                if cat_elem.text:
                    categories.append(cat_elem.text.strip())

            # 提取description（摘要）
            desc_elem = item_elem.find('description')
            description = None
            if desc_elem is not None and desc_elem.text:
                description = self._clean_html(desc_elem.text)

            # 提取完整内容（content:encoded）
            content_elem = item_elem.find('.//{http://purl.org/rss/1.0/modules/content/}encoded')
            content = None
            if content_elem is not None and content_elem.text:
                content = self._clean_html(content_elem.text)

            # 如果content为空，使用description或title
            if not content:
                content = description if description else title

            return {
                "external_id": external_id,
                "title": title,
                "content": content,
                "summary": description,  # RSS description已经是摘要
                "provider": author,
                "published_at": published_at,
                "url": url,
                "category": feed_category,
                "language": self.language,
                "tags": categories[:5] if categories else []  # 限制最多5个标签
            }
        except Exception as e:
            logger.error(f"Failed to extract article from RSS item: {e}", exc_info=True)
            return None

    def _extract_slug_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取slug作为ID

        Args:
            url: 文章URL，如 https://betakit.com/article-slug/

        Returns:
            slug作为ID
        """
        try:
            match = re.search(r'/([^/]+)/?$', url)
            return match.group(1) if match else None
        except Exception:
            return None

    def _clean_html(self, html_text: str) -> str:
        """
        清理HTML标签，提取纯文本

        Args:
            html_text: HTML文本

        Returns:
            纯文本
        """
        if not html_text:
            return ""

        # 移除HTML标签
        text = re.sub(r'<[^>]+>', ' ', html_text)
        # HTML实体解码
        text = unescape(text)
        # 合并多个空白
        text = re.sub(r'\s+', ' ', text)
        # 去除首尾空白
        text = text.strip()

        return text

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

    async def _preprocess_items(self, items: List[Dict[str, Any]]) -> None:
        """
        预处理：翻译summary + 字段增强（在数据库session外执行）

        Args:
            items: 文章列表（直接修改）
        """
        for item in items:
            try:
                # 1. 生成message_id（提前生成）
                item['message_id'] = str(uuid.uuid4())

                # 2. 翻译summary
                summary = await self._generate_summary(item.get('summary'), item.get('content', ''))
                item['summary_translated'] = summary

                # 3. 字段增强（region + industry_tags + ai_tag）
                if self.field_enricher:
                    enriched = await self.field_enricher.enrich_fields(
                        title=item['title'],
                        content=item.get('content', ''),
                        message_id=item['message_id'],
                        source_name="BetaKit"
                    )
                    item['region'] = enriched.get('region', self.region)
                    item['industry_tags'] = enriched.get('industry_tags', '')
                    item['ai_tag'] = enriched.get('ai_tag', '')
                else:
                    item['region'] = self.region
                    item['industry_tags'] = ''
                    item['ai_tag'] = ''

            except Exception as e:
                logger.error(f"预处理失败 {item.get('url')}: {e}")
                item['summary_translated'] = item.get('content', '')[:1000]
                item['region'] = self.region
                item['industry_tags'] = ''
                item['ai_tag'] = ''

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        """
        串行存储到MySQL和ChromaDB（使用预处理结果）

        注意：在Celery solo pool + nest_asyncio环境下，asyncio.gather会导致任务上下文冲突
        改为串行执行以保证稳定性

        Args:
            items: 文章列表（已包含翻译和增强字段）
        """
        await self._store_to_mysql(items)
        await self._store_to_chroma(items)

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到MySQL（使用预处理结果）

        Args:
            items: 文章列表
        """
        try:
            with create_session() as db:
                for item in items:
                    message = BetaKitMessage(
                        id=item.get('message_id', str(uuid.uuid4())),
                        source_id=self.source_id,
                        external_id=item.get('external_id'),
                        title=item['title'],
                        content=item['content'],
                        summary=item.get('summary_translated', ''),
                        provider=item.get('provider'),
                        published_at=item.get('published_at'),
                        crawled_at=datetime.now(),
                        url=item['url'],
                        region=item.get('region', self.region),
                        industry_tags=item.get('industry_tags', ''),
                        ai_tag=item.get('ai_tag', ''),
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

    async def _store_to_chroma(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到ChromaDB（使用预处理结果）

        Args:
            items: 文章列表
        """
        if not self.chroma_storage or not self.embedding_client:
            return

        try:
            for item in items:
                summary = item.get('summary_translated', '')
                document_text = f"{item['title']} {summary}"

                embedding = self.embedding_client.generate_embedding(document_text)

                # 使用external_id作为ChromaDB ID，确保与vector_sync一致
                chroma_id = item.get('external_id') or str(uuid.uuid4())

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

        外文内容全文翻译成中文，无需截断

        Args:
            summary: RSS提取的摘要
            content: 正文内容

        Returns:
            摘要文本（中文翻译）
        """
        source_text = summary if summary and len(summary.strip()) > 0 else content

        if not source_text:
            return ""

        # 中文内容直接返回
        if self.language == 'zh' or self._is_chinese(source_text):
            if len(source_text) <= 1000:
                return source_text
            else:
                return source_text[:1000] + "..."

        # 外文内容翻译
        if not self.translator:
            if len(source_text) > 1000:
                return source_text[:1000] + "..."
            return source_text

        try:
            translated = await self.translator.translate(
                text=source_text,
                context="BetaKit加拿大科技新闻"
            )
            return translated
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            fallback = source_text[:500] if len(source_text) > 500 else source_text
            return f"[AI翻译暂不可用] {fallback}"

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

        sample = text[:200]
        chinese_chars = len([c for c in sample if '\u4e00' <= c <= '\u9fff'])
        return chinese_chars / len(sample) > 0.3 if len(sample) > 0 else False
