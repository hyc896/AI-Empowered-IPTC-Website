# -*- coding: utf-8 -*-

"""
TechCrunch Tech News Collector
TechCrunch全球科技新闻与深度报道采集器
支持多分类采集：AI、Security、Robotics、Cloud Computing、Hardware等
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import Page
from sqlalchemy.exc import IntegrityError

from backend.collectors.base import PlaywrightCollectorBase
from backend.database.entities import TechCrunchMessage
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


class TechCrunchCollector(PlaywrightCollectorBase):
    """TechCrunch多分类科技新闻采集器"""

    CATEGORIES = {
        "AI": "https://techcrunch.com/category/artificial-intelligence/",
        "Security": "https://techcrunch.com/category/security/",
        "Robotics": "https://techcrunch.com/category/robotics/",
        "Cloud Computing": "https://techcrunch.com/tag/cloud-computing/",
        "Hardware": "https://techcrunch.com/category/hardware/",
        "Enterprise": "https://techcrunch.com/category/enterprise/",
        "Government & Policy": "https://techcrunch.com/category/government-policy/",
        "Privacy": "https://techcrunch.com/category/privacy/",
        "Biotech & Health": "https://techcrunch.com/category/biotech-health/"
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
                - region: 地区（默认GLOBAL）
                - language: 语言（en）
        """
        super().__init__(config)

        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.region = config['config'].get('region', 'GLOBAL')
        self.language = config['config'].get('language', 'en')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【TechCrunch】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
            self.field_enricher = get_field_enricher()
        else:
            self.embedding_client = None
            self.translator = None
            self.field_enricher = None
            logger.warning("【TechCrunch】LLM服务不可用，将跳过向量化、翻译和字段增强")

    async def _on_initialize(self) -> bool:
        """
        初始化钩子（创建ChromaDB collection）

        Returns:
            是否初始化成功
        """
        try:
            if self.chroma_storage:
                self.chroma_storage.create_collection(
                    collection_name=self.chroma_collection
                )

            logger.info(f"【TechCrunch】采集器初始化成功 (监控{len(self.CATEGORIES)}个分类)")
            return True
        except Exception as e:
            logger.error(f"【TechCrunch】采集器初始化失败: {e}")
            return False

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 遍历所有分类
        2. 获取MySQL中最新文章URL
        3. Playwright爬取分类页
        4. 过滤已存在URL
        5. 访问详情页获取完整内容
        6. 预翻译（session外）
        7. 并发存储到MySQL + ChromaDB
        """
        total_new_articles = 0

        for category_name, category_url in self.CATEGORIES.items():
            try:
                logger.info(f"【TechCrunch】开始采集分类: {category_name}")

                latest_url = await self._get_latest_stored_url(category_name)
                logger.debug(f"Latest stored URL for {category_name}: {latest_url}")

                articles_list = await self._scrape_category_list(category_url, category_name, latest_url)

                if not articles_list:
                    logger.debug(f"【{category_name}】No new items to collect")
                    continue

                new_items = self._filter_new_items(articles_list, latest_url)

                if new_items:
                    logger.info(f"【{category_name}】开始访问 {len(new_items)} 篇文章的详情页...")
                    for idx, item in enumerate(new_items, 1):
                        try:
                            full_content = await self._fetch_article_content(item['url'])
                            if full_content:
                                item['content'] = full_content
                                logger.debug(f"[{idx}/{len(new_items)}] ✓ 获取完整内容: {item['url']}")
                            else:
                                item['content'] = item['title']
                                logger.warning(f"[{idx}/{len(new_items)}] ⚠ 使用标题作为content: {item['url']}")
                        except Exception as e:
                            logger.error(f"[{idx}/{len(new_items)}] ✗ 详情页访问失败: {e}")
                            item['content'] = item['title']

                        await asyncio.sleep(1)

                    await self._store_items(new_items)
                    total_new_articles += len(new_items)
                    logger.info(f"【{category_name}】采集到 {len(new_items)} 篇新文章")
                else:
                    logger.debug(f"【{category_name}】所有文章已存在，无新数据")

                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"【TechCrunch】分类 {category_name} 采集错误: {e}", exc_info=True)

        if total_new_articles > 0:
            logger.info(f"【TechCrunch】本次采集共获取 {total_new_articles} 篇新文章")
        else:
            logger.info(f"【TechCrunch】本次采集无新文章")

    async def _get_latest_stored_url(self, category: str) -> Optional[str]:
        """
        获取MySQL中指定分类最新文章的URL（使用ORM）

        Args:
            category: 分类名称

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(TechCrunchMessage).filter(
                    TechCrunchMessage.source_id == self.source_id,
                    TechCrunchMessage.category == category,
                    TechCrunchMessage.url.isnot(None)
                ).order_by(
                    TechCrunchMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL for {category}: {e}")
            return None

    async def _scrape_category_list(
        self,
        category_url: str,
        category_name: str,
        latest_url: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Playwright爬取分类页，提取文章列表

        Args:
            category_url: 分类页URL
            category_name: 分类名称
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

                await page.goto(category_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"【{category_name}】第 {attempt + 1} 次尝试失败: {e}，{retry_delay}秒后重试...")
                    if page:
                        await page.close()
                        page = None
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【{category_name}】所有重试均失败: {e}", exc_info=True)
                    if page:
                        await page.close()
                    return []

        if not page:
            return []

        try:
            card_selector = ".loop-card--post-type-post"
            await page.wait_for_selector(card_selector, timeout=15000)

            card_elements = await page.query_selector_all(card_selector)
            logger.info(f"【{category_name}】找到 {len(card_elements)} 篇文章")

            articles = []
            for idx, card_elem in enumerate(card_elements):
                article_data = await self._extract_article_from_card(card_elem, category_name)
                if article_data:
                    articles.append(article_data)

                    if latest_url and article_data.get('url') == latest_url:
                        logger.debug(f"【{category_name}】遇到已存在URL，停止采集")
                        break

            await page.close()
            return articles

        except Exception as e:
            logger.error(f"【{category_name}】解析文章列表失败: {e}", exc_info=True)
            if page:
                await page.close()
            return []

    async def _extract_article_from_card(self, card_elem, category_name: str) -> Optional[Dict[str, Any]]:
        """
        从文章卡片元素提取数据

        Args:
            card_elem: 卡片DOM元素
            category_name: 分类名称

        Returns:
            文章数据字典
        """
        try:
            title_elem = await card_elem.query_selector("h2 a, h3 a")
            if not title_elem:
                return None

            title = (await title_elem.inner_text()).strip()
            url = await title_elem.get_attribute("href")

            if not url or not title:
                return None

            url = url if url.startswith('http') else f"https://techcrunch.com{url}"

            author_elem = await card_elem.query_selector(".loop-card__meta a, .loop-card__author")
            author = None
            if author_elem:
                author = (await author_elem.inner_text()).strip()

            time_elem = await card_elem.query_selector("time")
            published_at = datetime.now()
            if time_elem:
                datetime_str = await time_elem.get_attribute("datetime")
                if datetime_str:
                    try:
                        published_at = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                    except Exception:
                        pass

            external_id = self._extract_id_from_url(url)

            return {
                "external_id": external_id,
                "title": title,
                "content": title,
                "summary": None,
                "provider": author,
                "published_at": published_at,
                "url": url,
                "category": category_name,
                "language": self.language
            }
        except Exception as e:
            logger.error(f"Failed to extract article from card: {e}")
            return None

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取文章ID

        Args:
            url: 文章URL，如 https://techcrunch.com/2025/11/16/article-slug/

        Returns:
            文章路径slug作为ID
        """
        try:
            match = re.search(r'/(\d{4}/\d{2}/\d{2}/[^/]+)/?$', url)
            if match:
                return match.group(1)

            match = re.search(r'/([^/]+)/?$', url)
            return match.group(1) if match else None
        except Exception:
            return None

    async def _fetch_article_content(self, url: str) -> Optional[str]:
        """
        访问文章详情页，提取完整内容

        Args:
            url: 文章URL

        Returns:
            完整内容文本
        """
        page: Optional[Page] = None
        try:
            page = await self._browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            content_elem = await page.query_selector(".entry-content, .wp-block-post-content, article .article-content")
            if not content_elem:
                logger.warning(f"未找到内容元素: {url}")
                return None

            paragraphs = await content_elem.query_selector_all("p")
            content_parts = []

            for p in paragraphs:
                text = (await p.inner_text()).strip()
                if text and len(text) > 30:
                    content_parts.append(text)

            full_content = "\n\n".join(content_parts)

            await page.close()
            return full_content if full_content else None

        except Exception as e:
            logger.error(f"Failed to fetch article content from {url}: {e}")
            if page:
                await page.close()
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
        预翻译后并发存储到MySQL和ChromaDB（预翻译模式，避免session阻塞）

        Args:
            items: 文章列表
        """
        translations = {}
        enriched_fields = {}
        message_ids = {}  # 提前生成的message_id映射

        for item in items:
            # 提前生成message_id
            message_id = str(uuid.uuid4())
            message_ids[item['url']] = message_id

            try:
                summary = await self._generate_summary(item.get('summary'), item.get('content', ''))
                translations[item['url']] = summary

                if self.field_enricher:
                    enriched = await self.field_enricher.enrich_fields(
                        title=item['title'],
                        content=item.get('content', ''),
                        message_id=message_id,
                        source_name="TechCrunch"
                    )
                    enriched_fields[item['url']] = enriched
                else:
                    enriched_fields[item['url']] = {
                        'region': self.region,
                        'industry_tags': '',
                        'ai_tag': ''
                    }

            except Exception as e:
                logger.error(f"预处理失败 {item.get('url')}: {e}")
                translations[item['url']] = item.get('content', '')[:1000]
                enriched_fields[item['url']] = {
                    'region': self.region,
                    'industry_tags': '',
                    'ai_tag': ''
                }

        mysql_task = self._store_to_mysql(items, translations, enriched_fields, message_ids)
        chroma_task = self._store_to_chroma(items, translations)
        await asyncio.gather(mysql_task, chroma_task, return_exceptions=True)

    async def _store_to_mysql(
        self,
        items: List[Dict[str, Any]],
        translations: Dict[str, str],
        enriched_fields: Dict[str, Dict[str, str]],
        message_ids: Dict[str, str]
    ) -> None:
        """
        存储到MySQL（使用预翻译结果）

        Args:
            items: 文章列表
            translations: 预翻译结果字典
            enriched_fields: 预增强字段结果字典
            message_ids: 预生成的message_id字典
        """
        try:
            with create_session() as db:
                for item in items:
                    summary = translations.get(item['url'], '')
                    enriched = enriched_fields.get(item['url'], {})

                    message = TechCrunchMessage(
                        id=message_ids.get(item['url'], str(uuid.uuid4())),
                        source_id=self.source_id,
                        external_id=item.get('external_id'),
                        title=item['title'],
                        content=item['content'],
                        summary=summary,
                        provider=item.get('provider'),
                        published_at=item.get('published_at'),
                        crawled_at=datetime.now(),
                        url=item['url'],
                        region=enriched.get('region', self.region),
                        industry_tags=enriched.get('industry_tags', ''),
                        ai_tag=enriched.get('ai_tag', ''),
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

    async def _store_to_chroma(
        self,
        items: List[Dict[str, Any]],
        translations: Dict[str, str]
    ) -> None:
        """
        存储到ChromaDB（使用预翻译结果）

        Args:
            items: 文章列表
            translations: 预翻译结果字典
        """
        if not self.chroma_storage or not self.embedding_client:
            return

        try:
            for item in items:
                summary = translations.get(item['url'], '')
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
            summary: 网页提取的摘要（TechCrunch列表页无摘要字段）
            content: 正文内容

        Returns:
            摘要文本（中文翻译）
        """
        source_text = summary if summary and len(summary.strip()) > 0 else content

        if not source_text:
            return ""

        if self.language == 'zh' or self._is_chinese(source_text):
            if len(source_text) <= 1000:
                return source_text
            else:
                return source_text[:1000] + "..."

        if not self.translator:
            if len(source_text) > 1000:
                return source_text[:1000] + "..."
            return source_text

        try:
            translated = await self.translator.translate(
                text=source_text,
                context="TechCrunch科技新闻文章"
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
