# -*- coding: utf-8 -*-

"""
Tech in Asia News Collector
Tech in Asia东南亚科技创投新闻采集器
RSS Feed + Detail Page模式（Advanced Mode）
"""

import re
import uuid
import asyncio
import logging
import feedparser
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from playwright.async_api import Browser, Page
from sqlalchemy.exc import IntegrityError

from backend.database.entities import TechInAsiaMessage
from backend.database.connection import create_session
from backend.collectors.base import PlaywrightCollectorBase
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


class TechInAsiaCollector(PlaywrightCollectorBase):
    """Tech in Asia东南亚科技创投新闻采集器"""

    RSS_FEED_URL = "https://feeds.feedburner.com/techinasia"

    # Southeast Asian regions mapping (Chinese format)
    REGION_MAPPING = {
        'singapore': '新加坡',
        'indonesia': '印度尼西亚',
        'vietnam': '越南',
        'thailand': '泰国',
        'malaysia': '马来西亚',
        'philippines': '菲律宾',
        'korea': '韩国',
        'south korea': '韩国',
        'japan': '日本',
        'china': '中国',
        'india': '印度',
        'hong kong': '中国/香港',
        'taiwan': '中国/台湾',
        'asia': '亚洲',
        'southeast asia': '东南亚',
        'bengal': '印度/孟加拉',
        'bengaluru': '印度/班加罗尔'
    }

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - source_id: 消息源ID（关联message_sources表）
                - region: 地区（默认Southeast Asia）
                - language: 语言（en）
        """
        super().__init__(config)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.region = config['config'].get('region', 'Southeast Asia')
        self.language = config['config'].get('language', 'en')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【TechInAsia】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【TechInAsia】LLM服务不可用，将跳过向量化和翻译")

        if _field_enricher_available:
            self.field_enricher = get_field_enricher()
        else:
            self.field_enricher = None
            logger.warning("【TechInAsia】FieldEnricher不可用，将跳过字段增强")

    async def _on_initialize(self) -> bool:
        """
        子类初始化钩子：创建ChromaDB collection

        Returns:
            是否初始化成功
        """
        try:

            if self.chroma_storage:
                self.chroma_storage.create_collection(
                    collection_name=self.chroma_collection
                )

            logger.info(f"【TechInAsia】采集器初始化成功")
            return True
        except Exception as e:
            logger.error(f"【TechInAsia】采集器初始化失败: {e}")
            return False
    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 解析RSS feed获取元数据
        2. 获取MySQL中最新文章URL
        3. 过滤已存在URL
        4. 访问详情页获取完整内容
        5. 预处理（翻译、字段增强）
        6. 批量存储到MySQL + ChromaDB
        """
        logger.info(f"【TechInAsia】开始采集RSS feed")

        try:
            # 添加User-Agent头避免被屏蔽
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            feed = feedparser.parse(self.RSS_FEED_URL, request_headers=headers)

            if not feed.entries:
                logger.warning(f"【TechInAsia】RSS feed为空 (Bozo: {feed.bozo}, Status: {feed.get('status', 'N/A')})")
                if feed.bozo and hasattr(feed, 'bozo_exception'):
                    logger.error(f"【TechInAsia】RSS解析错误: {feed.bozo_exception}")
                return

            logger.info(f"【TechInAsia】RSS feed解析成功，共 {len(feed.entries)} 条记录")

            latest_url = await self._get_latest_stored_url()
            logger.debug(f"Latest stored URL: {latest_url}")

            articles_metadata = []
            for entry in feed.entries:
                url = entry.get('link', '')
                if not url:
                    continue

                if latest_url and url == latest_url:
                    logger.debug(f"遇到已存在URL，停止采集: {url}")
                    break

                item = {
                    'title': entry.get('title', '').strip(),
                    'url': url,
                    'author': entry.get('author', '').strip(),
                    'published': entry.get('published', ''),
                    'categories': [tag.get('term', '') for tag in entry.get('tags', [])],
                    'description': entry.get('summary', '').strip()
                }

                articles_metadata.append(item)

            if not articles_metadata:
                logger.info("【TechInAsia】没有新文章需要采集")
                return

            logger.info(f"【TechInAsia】发现 {len(articles_metadata)} 篇新文章，开始获取详情页内容...")

            for idx, item in enumerate(articles_metadata, 1):
                try:
                    full_content = await self._fetch_article_content(item['url'])
                    if full_content:
                        item['content'] = full_content
                        logger.debug(f"[{idx}/{len(articles_metadata)}] ✓ 获取完整内容: {item['url']}")
                    else:
                        item['content'] = item['description'] or item['title']
                        logger.warning(f"[{idx}/{len(articles_metadata)}] ⚠ 使用description作为content: {item['url']}")
                except Exception as e:
                    logger.error(f"[{idx}/{len(articles_metadata)}] ✗ 详情页访问失败: {e}")
                    item['content'] = item['description'] or item['title']

                await asyncio.sleep(1.5)

            await self._preprocess_and_store(articles_metadata)

            logger.info(f"【TechInAsia】本次采集完成，共处理 {len(articles_metadata)} 篇文章")

        except Exception as e:
            logger.error(f"【TechInAsia】采集过程出错: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新文章的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(TechInAsiaMessage).filter(
                    TechInAsiaMessage.source_id == self.source_id,
                    TechInAsiaMessage.url.isnot(None)
                ).order_by(
                    TechInAsiaMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL: {e}")
            return None

    async def _fetch_article_content(self, url: str) -> Optional[str]:
        """
        访问详情页获取完整文章内容

        Args:
            url: 文章URL

        Returns:
            完整内容，失败返回None
        """
        try:
            page: Page = await self._browser.new_page()
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)

            await asyncio.sleep(2)

            content_paragraphs = await page.query_selector_all('p')
            paragraphs_text = []

            for p in content_paragraphs:
                text = await p.inner_text()
                text = text.strip()

                if len(text) < 30:
                    continue
                if 'Copyright' in text or 'Business Times' in text:
                    continue
                if text.startswith('🔗') or text.startswith('👀'):
                    continue

                paragraphs_text.append(text)

            await page.close()

            if paragraphs_text:
                return '\n\n'.join(paragraphs_text)
            return None

        except Exception as e:
            logger.error(f"详情页访问失败 {url}: {e}")
            return None

    async def _preprocess_and_store(self, items: List[Dict[str, Any]]) -> None:
        """
        预处理并存储（预翻译模式）

        Args:
            items: 待处理的文章列表
        """
        if not items:
            return

        processed_items = []

        for item in items:
            try:
                summary_en = item.get('description', '')
                summary_zh = summary_en

                if self.translator and summary_en:
                    try:
                        summary_zh = await self.translator.translate(
                            summary_en,
                            context="Tech in Asia科技新闻摘要"
                        )
                    except Exception as e:
                        logger.warning(f"翻译失败，使用原文: {e}")
                        summary_zh = summary_en

                region_str = '全球'
                industry_tags_str = ''
                ai_tag_str = ''

                if self.field_enricher:
                    try:
                        enriched = await self.field_enricher.enrich_fields(
                            title=item['title'],
                            content=item['content']
                        )
                        region_str = enriched.get('region', '全球')
                        industry_tags_str = enriched.get('industry_tags', '')
                        ai_tag_str = enriched.get('ai_tag', '')
                    except Exception as e:
                        logger.warning(f"字段增强失败: {e}")

                if not region_str or region_str == '全球':
                    detected_region = self._detect_region_from_categories(item['categories'])
                    if detected_region:
                        region_str = detected_region

                processed_item = {
                    'url': item['url'],
                    'title': item['title'],
                    'content': item['content'],
                    'summary': summary_zh,
                    'provider': item['author'],
                    'published_at': self._parse_datetime(item['published']),
                    'categories': item['categories'],
                    'region': region_str,
                    'industry_tags': industry_tags_str,
                    'ai_tag': ai_tag_str
                }

                processed_items.append(processed_item)

            except Exception as e:
                logger.error(f"预处理失败 {item.get('url')}: {e}")

        if processed_items:
            await self._store_items(processed_items)

    def _detect_region_from_categories(self, categories: List[str]) -> Optional[str]:
        """
        从分类标签中检测地区

        Args:
            categories: 分类标签列表

        Returns:
            检测到的地区（中文），未检测到返回None
        """
        for category in categories:
            category_lower = category.lower()
            for key, value in self.REGION_MAPPING.items():
                if key in category_lower:
                    return value
        return None

    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """
        解析RSS日期字符串

        Args:
            date_str: 日期字符串

        Returns:
            datetime对象，解析失败返回None
        """
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception:
            return None

    def _extract_external_id(self, url: str) -> str:
        """
        从URL提取external_id（URL slug）

        Args:
            url: 文章URL

        Returns:
            external_id
        """
        try:
            path = urlparse(url).path
            slug = path.strip('/').split('/')[-1]
            return slug[:200]
        except Exception:
            return str(uuid.uuid4())

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        """
        批量存储到MySQL和ChromaDB

        流程（VentureBeat模式）：
        1. MySQL存储（仅DB操作）
        2. ChromaDB存储（在DB session外，包含向量化）

        Args:
            items: 待存储的文章列表
        """
        if not items:
            return

        stored_count = 0
        duplicate_count = 0
        stored_records = []  # 收集成功存储的记录信息

        # ===== 阶段1: MySQL存储（仅DB操作） =====
        with create_session() as db:
            for item in items:
                try:
                    message_id = str(uuid.uuid4())
                    external_id = self._extract_external_id(item['url'])

                    category_str = ', '.join(item.get('categories', []))[:100] if item.get('categories') else ''

                    message = TechInAsiaMessage(
                        id=message_id,
                        source_id=self.source_id,
                        external_id=external_id,
                        title=item['title'],
                        content=item['content'],
                        summary=item.get('summary', ''),
                        provider=item.get('provider', ''),
                        published_at=item.get('published_at'),
                        crawled_at=datetime.now(),
                        url=item['url'],
                        region=item.get('region', '全球'),
                        industry_tags=item.get('industry_tags', ''),
                        ai_tag=item.get('ai_tag', ''),
                        category=category_str,
                        language=self.language
                    )

                    db.add(message)
                    db.commit()

                    # 收集成功存储的记录信息（用于后续向量化）
                    stored_records.append({
                        'message_id': message_id,
                        'external_id': external_id,
                        'item': item
                    })
                    stored_count += 1

                except IntegrityError:
                    db.rollback()
                    duplicate_count += 1
                    logger.debug(f"重复记录，跳过: {item['url']}")
                except Exception as e:
                    db.rollback()
                    logger.error(f"存储失败 {item['url']}: {e}")

        # ===== 阶段2: ChromaDB存储（在DB session外） =====
        if self.chroma_storage and self.chroma_storage.is_initialized() and self.embedding_client:
            for record in stored_records:
                try:
                    item = record['item']
                    embedding = await self.embedding_client.create_embedding(item['content'])
                    # 使用external_id作为ChromaDB ID，确保与vector_sync一致
                    self.chroma_storage.upsert(
                        collection_name=self.chroma_collection,
                        ids=[record['external_id']],
                        documents=[item['content']],
                        embeddings=[embedding],
                        metadatas=[{
                            'id': record['message_id'],
                            'source_id': self.source_id,
                            'title': item['title'][:500],
                            'summary': item.get('summary', '')[:1000],
                            'published_at': item.get('published_at').isoformat() if item.get('published_at') else '',
                            'url': item['url']
                        }]
                    )
                except Exception as e:
                    logger.warning(f"向量化失败 {item['url']}: {e}")

        if stored_count > 0:
            logger.info(f"【TechInAsia】成功存储 {stored_count} 条新记录")
        if duplicate_count > 0:
            logger.debug(f"【TechInAsia】跳过 {duplicate_count} 条重复记录")


async def main():
    """测试入口"""
    import sys
    sys.path.insert(0, 'D:\\TechWork\\message_platform')

    config = {
        'id': 'test-source-id',
        'interval': 3600,
        'mysql_table': 'mp_techinasia_messages',
        'chroma_collection': 'techinasia',
        'config': {
            'region': 'Southeast Asia',
            'language': 'en'
        }
    }

    collector = TechInAsiaCollector(config)
    await collector.initialize()
    await collector._collect_once()
    await collector.stop()


if __name__ == '__main__':
    asyncio.run(main())
