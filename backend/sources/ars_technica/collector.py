# -*- coding: utf-8 -*-

"""
ArsTechnica Technology News Collector
ArsTechnica科技新闻采集器（基于RSS Feed）

数据来源：
- RSS Feed: https://feeds.arstechnica.com/arstechnica/index
- 格式：标准RSS 2.0
- 频率：每次约50条新闻
- 地区：美国
- 语言：英语

架构特点：
- 纯RSS模式：无需访问详情页，RSS内容已足够完整
- 预翻译模式：在数据库会话外完成翻译
- 预增强模式：在数据库会话外完成字段增强（region + industry_tags + ai_tag）
- 滑动验证去重：启动时查询最新URL，遇到已存在记录立即停止
"""

import re
import uuid
import asyncio
import logging
import feedparser
from datetime import datetime
from typing import Dict, Any, List, Optional
from time import mktime
from sqlalchemy.exc import IntegrityError

from backend.database.entities import ArsTechnicaMessage
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


class ArsTechnicaCollector:
    """ArsTechnica Technology新闻采集器（RSS Feed模式）"""

    RSS_FEED_URL = "https://feeds.arstechnica.com/arstechnica/index"

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - id: 消息源ID（关联message_sources表）
                - interval: 采集间隔（秒）
                - config.mysql_table: MySQL表名
                - config.chroma_collection: ChromaDB collection名称
                - config.region: 默认地区
                - config.language: 语言（en）
        """
        self.source_id = config.get('id', 'auto')
        self.interval = config.get('interval', 3600)

        config_detail = config.get('config', {})
        self.mysql_table = config_detail.get('mysql_table', 'mp_ars_technica_messages')
        self.chroma_collection = config_detail.get('chroma_collection', 'ars_technica_tech')
        self.region = config_detail.get('region', '美国')
        self.language = config_detail.get('language', 'en')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【ArsTechnica】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
            self.field_enricher = get_field_enricher()
        else:
            self.embedding_client = None
            self.translator = None
            self.field_enricher = None
            logger.warning("【ArsTechnica】LLM服务不可用，将跳过向量化、翻译和字段增强")

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

            logger.info(f"【ArsTechnica】采集器初始化成功")
            return True
        except Exception as e:
            logger.error(f"【ArsTechnica】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【ArsTechnica】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【ArsTechnica】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【ArsTechnica】采集失败: {e}", exc_info=True)

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        logger.info("【ArsTechnica】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 解析RSS feed获取所有条目
        2. 获取MySQL中最新文章URL
        3. 遇到已存在URL立即停止（滑动验证去重）
        4. 预处理（翻译、字段增强）
        5. 批量存储到MySQL + ChromaDB
        """
        logger.info(f"【ArsTechnica】开始采集RSS feed")

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            feed = feedparser.parse(self.RSS_FEED_URL, request_headers=headers)

            if not feed.entries:
                logger.warning(f"【ArsTechnica】RSS feed为空 (Bozo: {feed.bozo}, Status: {feed.get('status', 'N/A')})")
                if feed.bozo and hasattr(feed, 'bozo_exception'):
                    logger.error(f"【ArsTechnica】RSS解析错误: {feed.bozo_exception}")
                return

            logger.info(f"【ArsTechnica】RSS feed解析成功，共 {len(feed.entries)} 条记录")

            latest_url = await self._get_latest_stored_url()
            logger.debug(f"【ArsTechnica】最新存储URL: {latest_url}")

            articles = []
            for entry in feed.entries:
                url = entry.get('link', '').strip()
                if not url:
                    continue

                if latest_url and url == latest_url:
                    logger.info(f"【ArsTechnica】遇到已存在URL，停止采集: {url}")
                    break

                guid = entry.get('id') or entry.get('guid')
                if isinstance(guid, dict):
                    guid = guid.get('href', '')

                title = entry.get('title', '').strip()
                description = entry.get('description') or entry.get('summary', '')
                description = self._clean_html(description)

                author = entry.get('author', '').strip()
                if not author and hasattr(entry, 'dc_creator'):
                    author = entry.dc_creator

                published_parsed = entry.get('published_parsed')
                published_at = None
                if published_parsed:
                    try:
                        published_at = datetime.fromtimestamp(mktime(published_parsed))
                    except Exception as e:
                        logger.warning(f"【ArsTechnica】解析发布时间失败: {e}")

                categories = []
                if hasattr(entry, 'tags'):
                    categories = [tag.get('term', '') for tag in entry.tags if tag.get('term')]

                media_url = None
                if hasattr(entry, 'media_content'):
                    media_content = entry.media_content
                    if isinstance(media_content, list) and len(media_content) > 0:
                        media_url = media_content[0].get('url', '')

                # 处理category：连接所有标签，限制最大长度为490字符（防止超过数据库VARCHAR(500)限制）
                category_str = ', '.join(categories) if categories else None
                if category_str and len(category_str) > 490:
                    category_str = category_str[:490]

                item = {
                    'external_id': guid,
                    'title': title,
                    'content': description,
                    'url': url,
                    'provider': author,
                    'published_at': published_at,
                    'category': category_str,
                    'media_content': media_url,
                    'tags': categories
                }

                articles.append(item)

            if not articles:
                logger.info("【ArsTechnica】没有新文章需要采集")
                return

            logger.info(f"【ArsTechnica】发现 {len(articles)} 篇新文章，开始预处理...")

            await self._preprocess_and_store(articles)

            logger.info(f"【ArsTechnica】本次采集完成，共处理 {len(articles)} 篇文章")

        except Exception as e:
            logger.error(f"【ArsTechnica】采集过程出错: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新文章的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(ArsTechnicaMessage).filter(
                    ArsTechnicaMessage.source_id == self.source_id,
                    ArsTechnicaMessage.url.isnot(None)
                ).order_by(
                    ArsTechnicaMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"【ArsTechnica】获取最新URL失败: {e}")
            return None

    def _clean_html(self, text: str) -> str:
        """
        清理HTML标签

        Args:
            text: 原始文本（可能包含HTML）

        Returns:
            清理后的文本
        """
        if not text:
            return ''

        text = re.sub(r'<br\s*/?\s*>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&quot;', '"', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)

        text = '\n'.join([line.strip() for line in text.split('\n') if line.strip()])

        return text.strip()

    async def _preprocess_and_store(self, items: List[Dict[str, Any]]) -> None:
        """
        预处理并存储（预翻译+预增强模式）

        Args:
            items: 待处理的文章列表
        """
        if not items:
            return

        processed_items = []

        for item in items:
            try:
                summary_en = item.get('content', '')
                summary_zh = summary_en

                if self.translator and summary_en:
                    try:
                        summary_zh = await self.translator.translate(
                            summary_en,
                            context="ArsTechnica科技新闻摘要"
                        )
                    except Exception as e:
                        logger.warning(f"【ArsTechnica】翻译失败，使用原文: {e}")
                        summary_zh = summary_en

                region_str = self.region
                industry_tags_str = ''
                ai_tag_str = ''

                if self.field_enricher:
                    try:
                        enriched = await self.field_enricher.enrich_fields(
                            title=item['title'],
                            content=summary_en
                        )
                        region_str = enriched.get('region', self.region)
                        industry_tags_str = enriched.get('industry_tags', '')
                        ai_tag_str = enriched.get('ai_tag', '')
                        logger.debug(f"【ArsTechnica】字段增强成功: region={region_str}, industry_tags={industry_tags_str}, ai_tag={ai_tag_str}")
                    except Exception as e:
                        logger.warning(f"【ArsTechnica】字段增强失败，使用默认值: {e}")

                processed_item = {
                    'external_id': item.get('external_id'),
                    'title': item['title'],
                    'content': item['content'],
                    'summary': summary_zh,
                    'url': item['url'],
                    'provider': item.get('provider'),
                    'published_at': item.get('published_at'),
                    'category': item.get('category'),
                    'media_content': item.get('media_content'),
                    'tags': item.get('tags'),
                    'region': region_str,
                    'industry_tags': industry_tags_str,
                    'ai_tag': ai_tag_str,
                    'language': self.language
                }

                processed_items.append(processed_item)

            except Exception as e:
                logger.error(f"【ArsTechnica】预处理失败: {e}", exc_info=True)
                continue

        if not processed_items:
            logger.warning("【ArsTechnica】预处理后无有效数据")
            return

        await self._store_to_mysql(processed_items)

        if self.chroma_storage and self.chroma_storage.is_initialized():
            try:
                await self._sync_to_chromadb(processed_items)
            except Exception as e:
                logger.error(f"【ArsTechnica】向量化失败: {e}", exc_info=True)

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到MySQL（仅做数据库CRUD，不调用外部服务）

        Args:
            items: 待存储的文章列表（已完成预处理）
        """
        if not items:
            return

        stored_count = 0
        duplicate_count = 0

        with create_session() as db:
            for item in items:
                try:
                    message = ArsTechnicaMessage(
                        id=str(uuid.uuid4()),
                        source_id=self.source_id,
                        external_id=item.get('external_id'),
                        title=item['title'],
                        content=item['content'],
                        summary=item.get('summary'),
                        provider=item.get('provider'),
                        published_at=item.get('published_at'),
                        crawled_at=datetime.now(),
                        url=item['url'],
                        region=item.get('region'),
                        industry_tags=item.get('industry_tags'),
                        ai_tag=item.get('ai_tag'),
                        category=item.get('category'),
                        language=item.get('language'),
                        media_content=item.get('media_content'),
                        tags=item.get('tags')
                    )

                    db.add(message)
                    db.commit()
                    stored_count += 1

                except IntegrityError as e:
                    db.rollback()
                    duplicate_count += 1
                    logger.debug(f"【ArsTechnica】重复记录（URL已存在）: {item['url']}")
                except Exception as e:
                    db.rollback()
                    logger.error(f"【ArsTechnica】存储失败: {e}", exc_info=True)

        logger.info(f"【ArsTechnica】MySQL存储完成: 成功={stored_count}, 重复={duplicate_count}")

    async def _sync_to_chromadb(self, items: List[Dict[str, Any]]) -> None:
        """
        同步到ChromaDB（批量upsert）

        Args:
            items: 待向量化的文章列表
        """
        if not items or not self.embedding_client:
            return

        try:
            ids = []
            documents = []
            metadatas = []

            embeddings = []
            for item in items:
                doc_id = item.get('external_id') or item['url']
                ids.append(doc_id)

                doc_text = f"{item['title']}\n\n{item.get('summary', item['content'])}"
                documents.append(doc_text)

                metadata = {
                    'source_id': self.source_id,
                    'title': item['title'],
                    'url': item['url'],
                    'provider': item.get('provider', ''),
                    'published_at': item.get('published_at').isoformat() if item.get('published_at') else '',
                    'category': item.get('category', ''),
                    'region': item.get('region', ''),
                    'industry_tags': item.get('industry_tags', ''),
                    'ai_tag': item.get('ai_tag', '')
                }
                metadatas.append(metadata)

                # 生成embedding（同步方法，不需要await）
                embedding = self.embedding_client.generate_embedding(doc_text)
                embeddings.append(embedding)

            self.chroma_storage.upsert(
                collection_name=self.chroma_collection,
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )

            logger.info(f"【ArsTechnica】ChromaDB同步完成: {len(ids)} 条记录")

        except Exception as e:
            logger.error(f"【ArsTechnica】ChromaDB同步失败: {e}", exc_info=True)
