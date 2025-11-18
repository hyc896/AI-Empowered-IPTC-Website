# -*- coding: utf-8 -*-

"""
Investing.com RSS Collector
全球金融市场综合新闻采集器（RSS订阅源）

技术特点：
- 使用feedparser解析RSS
- 无需Playwright，直接HTTP请求
- 字段映射：guid→external_id, link→url, description→content/summary
- 去重策略：url字段UNIQUE约束
"""

import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from email.utils import parsedate_to_datetime

try:
    import feedparser
    _feedparser_available = True
except ImportError:
    _feedparser_available = False
    feedparser = None

from sqlalchemy.exc import IntegrityError

from backend.database.entities import InvestingComMessage
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


class InvestingComCollector:
    """Investing.com RSS财经快讯采集器"""

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
                  - url: RSS订阅源URL
        """
        if not _feedparser_available:
            raise ImportError(
                "feedparser库未安装，请运行: pip install feedparser\n"
                "用于解析RSS/XML格式的订阅源"
            )

        self.source_id = config['id']
        self.interval = config['config'].get('interval', 30)
        self.mysql_table = config['config']['mysql_table']
        self.chroma_collection = config['config']['chroma_collection']

        # 支持多RSS源配置（向后兼容单URL格式）
        if 'rss_feeds' in config['config']:
            self.rss_feeds = config['config']['rss_feeds']
        else:
            # 向后兼容：单个url转换为列表格式
            self.rss_feeds = [{
                "url": config['config'].get('url', 'https://www.investing.com/rss/news.rss'),
                "category": "General News"
            }]

        # 优雅地处理缺失的依赖
        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【Investing.com】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【Investing.com】LLM服务不可用，将跳过向量化和翻译")

        if _field_enricher_available:
            self.field_enricher = get_field_enricher()
        else:
            self.field_enricher = None
            logger.warning("【Investing.com】FieldEnricher不可用，将跳过字段增强")

        self._running = False

    async def initialize(self) -> bool:
        """
        初始化采集器

        Returns:
            是否初始化成功
        """
        try:
            if self.chroma_storage:
                self.chroma_storage.create_collection(
                    collection_name=self.chroma_collection
                )

            logger.info(f"【Investing.com】采集器初始化成功: {len(self.rss_feeds)}个RSS源")
            return True
        except Exception as e:
            logger.error(f"【Investing.com】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【Investing.com】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【Investing.com】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【Investing.com】采集失败: {e}", exc_info=True)

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        logger.info("【Investing.com】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集（并发处理多个RSS源）

        流程：
        1. 并发采集所有RSS源
        2. 合并所有源的新闻列表
        3. 批量存储到MySQL + ChromaDB
        """
        try:
            # 并发采集所有RSS源
            tasks = [
                self._parse_single_feed(feed['url'], feed['category'])
                for feed in self.rss_feeds
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 统计各源采集结果
            all_news = []
            for i, result in enumerate(results):
                feed_info = self.rss_feeds[i]
                if isinstance(result, Exception):
                    logger.error(f"【Investing.com-{feed_info['category']}】采集失败: {result}")
                else:
                    all_news.extend(result)
                    if result:
                        logger.debug(f"【Investing.com-{feed_info['category']}】采集到 {len(result)} 条新闻")

            if all_news:
                await self._store_items(all_news)
                logger.info(f"【Investing.com】总计采集 {len(all_news)} 条新快讯（来自{len(self.rss_feeds)}个RSS源）")
            else:
                logger.debug("【Investing.com】所有源无新数据")

        except Exception as e:
            logger.error(f"【Investing.com】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self, category: Optional[str] = None) -> Optional[str]:
        """
        获取MySQL中最新新闻的URL（可按category过滤）

        Args:
            category: 新闻分类（可选），用于按分类查询最新URL

        Returns:
            最新新闻URL，如果没有返回None
        """
        try:
            with create_session() as db:
                query = db.query(InvestingComMessage).filter(
                    InvestingComMessage.url.isnot(None)
                )

                # 如果提供category，按分类查询最新（避免误判）
                if category:
                    query = query.filter(InvestingComMessage.category == category)

                latest = query.order_by(
                    InvestingComMessage.crawled_at.desc()
                ).first()

                if latest and latest.url:
                    category_info = f" (category={category})" if category else ""
                    logger.debug(f"Latest stored{category_info}: url={latest.url}, crawled_at={latest.crawled_at}")
                    return latest.url
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL: {e}")
            return None

    async def _parse_single_feed(self, rss_url: str, category: str) -> List[Dict[str, Any]]:
        """
        解析单个RSS源

        Args:
            rss_url: RSS订阅源URL
            category: 新闻分类（General News/Forex/Commodities/Crypto）

        Returns:
            新闻列表（已注入category字段）
        """
        try:
            # 按category查询最新URL（提高去重效率）
            latest_url = await self._get_latest_stored_url(category)

            logger.debug(f"Fetching RSS from: {rss_url} (category={category})")

            # feedparser.parse是同步函数，在asyncio中使用
            feed = await asyncio.to_thread(feedparser.parse, rss_url)

            if feed.bozo:
                logger.warning(f"RSS解析警告 ({category}): {feed.bozo_exception}")

            news_list = []

            for entry in feed.entries:
                try:
                    link = entry.get('link', '')
                    if not link:
                        logger.warning(f"RSS条目缺少link字段 ({category})，跳过")
                        continue

                    # 去重检查：遇到latest_url立即停止
                    if latest_url and link == latest_url:
                        logger.debug(f"Reached latest stored URL ({category}), stopping")
                        break

                    article_data = self._extract_article_from_entry(entry)
                    if article_data:
                        # 注入category字段
                        article_data['category'] = category
                        news_list.append(article_data)

                except Exception as e:
                    logger.error(f"Failed to extract RSS entry ({category}): {e}")
                    continue

            logger.debug(f"Parsed {len(news_list)} new items from {category}")
            return news_list

        except Exception as e:
            logger.error(f"Failed to parse RSS feed ({category}): {e}", exc_info=True)
            return []

    def _extract_article_id(self, url: str) -> str:
        """
        从URL中提取文章ID

        Args:
            url: 完整URL

        Returns:
            文章ID（URL末尾的数字，或URL的哈希值）

        示例：
            'https://www.investing.com/news/category/title-4363155' -> '4363155'
        """
        try:
            # 尝试提取URL末尾的数字ID
            import re
            match = re.search(r'-(\d+)$', url)
            if match:
                return match.group(1)

            # 如果没有找到数字ID，使用URL的哈希值（前16位）
            import hashlib
            url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
            logger.warning(f"无法从URL提取文章ID，使用哈希值: {url_hash}")
            return url_hash

        except Exception as e:
            logger.error(f"提取文章ID失败: {e}，使用URL前100字符")
            return url[:100]

    def _extract_article_from_entry(self, entry: Any) -> Optional[Dict[str, Any]]:
        """
        从RSS条目中提取文章数据

        Args:
            entry: feedparser解析的单个RSS条目

        Returns:
            文章数据字典
        """
        try:
            # 必备字段
            title = entry.get('title', '').strip()
            link = entry.get('link', '').strip()

            # 提取external_id：从URL末尾提取文章ID（如4363155）
            # URL格式：https://www.investing.com/news/category/article-title-1234567
            guid = entry.get('guid', entry.get('id', link)).strip()
            external_id = self._extract_article_id(guid)

            if not title or not link:
                logger.warning("RSS条目缺少title或link，跳过")
                return None

            # 内容字段映射
            description = entry.get('description', entry.get('summary', '')).strip()
            content = description if description else title
            summary = description if description else title

            # 发布时间解析
            published_at = None
            if 'published_parsed' in entry and entry.published_parsed:
                try:
                    from time import struct_time
                    import time
                    if isinstance(entry.published_parsed, struct_time):
                        published_at = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                except Exception as e:
                    logger.warning(f"Failed to parse published_parsed: {e}")

            if not published_at and 'published' in entry:
                try:
                    published_at = parsedate_to_datetime(entry.published)
                except Exception as e:
                    logger.warning(f"Failed to parse pubDate: {e}")

            if not published_at:
                published_at = datetime.now()

            return {
                "title": title,
                "content": content,
                "summary": summary,
                "provider": "Investing.com",
                "published_at": published_at,
                "url": link,
                "external_id": external_id,
                "category": "General News"
            }

        except Exception as e:
            logger.error(f"Failed to extract article from entry: {e}")
            return None

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        """
        并发存储到MySQL和ChromaDB

        Args:
            items: 新闻列表
        """
        mysql_task = self._store_to_mysql(items)
        chroma_task = self._store_to_chroma(items)
        await asyncio.gather(mysql_task, chroma_task, return_exceptions=True)

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到MySQL（预增强模式：在事务外完成字段增强）

        Args:
            items: 新闻列表
        """
        try:
            # 预增强：在数据库事务外批量增强字段和翻译摘要
            logger.debug(f"【Investing.com】批量处理 {len(items)} 条消息（字段增强 + 摘要翻译）")
            for item in items:
                # 提前生成message_id用于事件发布
                message_id = str(uuid.uuid4())
                item['message_id'] = message_id

                # 1. 字段增强（region, industry_tags, ai_tag）
                if self.field_enricher:
                    try:
                        enriched = await self.field_enricher.enrich_fields(
                            title=item['title'],
                            content=item['content'],
                            message_id=message_id,
                            source_name="Investing.com"
                        )
                        item['region'] = enriched.get('region')
                        item['industry_tags'] = enriched.get('industry_tags')
                        item['ai_tag'] = enriched.get('ai_tag')
                    except Exception as e:
                        logger.error(f"【Investing.com】字段增强失败: {e}")
                        item['region'] = None
                        item['industry_tags'] = None
                        item['ai_tag'] = None
                else:
                    item['region'] = None
                    item['industry_tags'] = None
                    item['ai_tag'] = None

                # 2. 摘要翻译（英文→中文）
                item['summary'] = await self._generate_summary(item.get('summary'), item.get('content', ''))

            # 批量存储到数据库
            with create_session() as db:
                for item in items:
                    message = InvestingComMessage(
                        id=item.get('message_id', str(uuid.uuid4())),
                        source_id=self.source_id,
                        external_id=item.get('external_id'),
                        title=item['title'],
                        content=item['content'],
                        summary=item.get('summary'),
                        provider=item.get('provider'),
                        published_at=item.get('published_at'),
                        url=item['url'],
                        region=item.get('region'),
                        industry_tags=item.get('industry_tags'),
                        ai_tag=item.get('ai_tag'),
                        category=item.get('category'),
                        language='en',
                        crawled_at=datetime.now()
                    )

                    try:
                        db.add(message)
                        db.commit()
                        logger.debug(f"Inserted to MySQL: url={item['url']}")
                    except IntegrityError as e:
                        db.rollback()
                        if "Duplicate entry" in str(e):
                            logger.debug(f"Duplicate URL: {item['url']}")
                        else:
                            logger.error(f"MySQL insert error: {e}")
        except Exception as e:
            logger.error(f"Failed to store to MySQL: {e}", exc_info=True)

    async def _store_to_chroma(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到ChromaDB

        Args:
            items: 新闻列表
        """
        if not self.chroma_storage or not self.embedding_client:
            return

        try:
            for item in items:
                summary = item.get('summary', item['content'])
                document_text = f"{item['title']} {summary}"

                embedding = self.embedding_client.generate_embedding(document_text)

                # 使用external_id作为ChromaDB的ID（稳定唯一）
                chroma_id = item.get('external_id') or item.get('url') or str(uuid.uuid4())

                self.chroma_storage.upsert(
                    collection_name=self.chroma_collection,
                    ids=[str(chroma_id)],
                    documents=[document_text],
                    metadatas=[{
                        "source_id": self.source_id,
                        "provider": item.get('provider', ''),
                        "category": item.get('category', 'General News'),
                        "published_at": item['published_at'].isoformat() if item.get('published_at') else '',
                        "url": item['url'],
                        "title": item['title']
                    }],
                    embeddings=[embedding]
                )
                logger.debug(f"Inserted to ChromaDB: chroma_id={chroma_id}")
        except Exception as e:
            logger.error(f"Failed to store to ChromaDB: {e}", exc_info=True)

    async def _generate_summary(self, summary: Optional[str], content: str) -> str:
        """
        生成中文摘要（英文→中文翻译）

        Investing.com是纯英文源，所有summary都需要翻译成中文

        Args:
            summary: RSS的description字段（英文）
            content: 正文内容（英文）

        Returns:
            中文摘要
        """
        # 1. 确定原始文本来源
        source_text = summary if summary and len(summary.strip()) > 0 else content

        if not source_text:
            return ""

        # 2. 翻译成中文
        if self.translator:
            try:
                # 限制长度（translator内部会处理超长文本）
                text_to_translate = source_text if len(source_text) <= 2000 else source_text[:2000]

                translated = await self.translator.translate(
                    text_to_translate,
                    context="Investing.com全球金融市场新闻摘要"
                )
                return translated
            except Exception as e:
                logger.error(f"【Investing.com】摘要翻译失败: {e}")
                # 降级策略：返回截断原文并标记
                return source_text[:500] + "... [AI翻译暂不可用]"
        else:
            # 无翻译器：返回截断的英文原文
            if len(source_text) <= 1000:
                return source_text
            return source_text[:500] + "..."
