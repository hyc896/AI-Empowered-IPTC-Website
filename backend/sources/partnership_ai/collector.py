# -*- coding: utf-8 -*-

"""
Partnership on AI Collector
人工智能伙伴关系组织博客采集器
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import Browser, Page
from sqlalchemy.exc import IntegrityError

from backend.database.entities import PartnershipAIMessage
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


class PartnershipAICollector(PlaywrightCollectorBase):
    """Partnership on AI博客采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - url: Partnership on AI博客URL
                - source_id: 消息源ID（关联message_sources表）
                - region: 地区（US）
                - timezone: 时区（America/New_York）
                - language: 语言（en）
        """
        super().__init__(config)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.url = config['config'].get('url', 'https://partnershiponai.org/blog/')
        self.region = config['config'].get('region', 'US')
        self.timezone = config['config'].get('timezone', 'America/New_York')
        self.language = config['config'].get('language', 'en')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【Partnership AI】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【Partnership AI】LLM服务不可用，将跳过向量化和翻译")

        if _field_enricher_available:
            self.field_enricher = get_field_enricher()
        else:
            self.field_enricher = None
            logger.warning("【Partnership AI】FieldEnricher不可用，将跳过字段增强")

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

            logger.info(f"【Partnership AI】采集器初始化成功: {self.url}")
            return True
        except Exception as e:
            logger.error(f"【Partnership AI】采集器初始化失败: {e}")
            return False



    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新文章URL
        2. Playwright爬取博客页
        3. 过滤已存在URL
        4. 并发存储到MySQL + ChromaDB
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
                logger.info(f"【Partnership AI】开始访问 {len(new_items)} 篇文章的详情页...")
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

                # 预处理（翻译+字段增强）
                await self._preprocess_items(new_items)

                await self._store_items(new_items)
                logger.info(f"【Partnership AI】采集到 {len(new_items)} 篇新文章")
            else:
                logger.debug("【Partnership AI】所有文章已存在，无新数据")

        except Exception as e:
            logger.error(f"【Partnership AI】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新文章的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(PartnershipAIMessage).filter(
                    PartnershipAIMessage.source_id == self.source_id,
                    PartnershipAIMessage.url.isnot(None)
                ).order_by(
                    PartnershipAIMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL: {e}")
            return None

    async def _scrape_articles_list(self, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        Playwright爬取博客页，提取文章列表

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
                await asyncio.sleep(3)
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"【Partnership AI】第 {attempt + 1} 次尝试失败: {e}，{retry_delay}秒后重试...")
                    if page:
                        await page.close()
                        page = None
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【Partnership AI】所有重试均失败: {e}", exc_info=True)
                    if page:
                        await page.close()
                    return []

        if not page:
            return []

        try:
            articles_selector = "a.post-card"
            await page.wait_for_selector(articles_selector, timeout=15000)

            article_elements = await page.query_selector_all(articles_selector)
            logger.debug(f"Found {len(article_elements)} post-card elements")

            articles_list = []
            for article_elem in article_elements:
                article_data = await self._extract_article_from_element(article_elem)

                if not article_data:
                    continue

                article_url = article_data.get('url')
                if not article_url:
                    continue

                if latest_url and article_url == latest_url:
                    logger.debug(f"Reached latest stored URL ({latest_url}), stopping")
                    break

                articles_list.append(article_data)

            return articles_list

        except Exception as e:
            logger.error(f"Failed to scrape articles list: {e}", exc_info=True)
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
            await asyncio.sleep(1)

            # 提取文章正文内容
            paragraphs = await detail_page.query_selector_all('article p, .entry-content p')
            content_parts = []

            for para in paragraphs:
                para_text = (await para.inner_text()).strip()
                # 过滤掉非正文内容
                if para_text and para_text not in ['Share', '']:
                    # 排除作者信息行
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

    async def _extract_article_from_element(self, article_elem) -> Optional[Dict[str, Any]]:
        """
        从post-card元素中提取文章数据

        Args:
            article_elem: a.post-card DOM元素

        Returns:
            文章数据字典
        """
        try:
            url = await article_elem.get_attribute("href")
            if not url:
                return None

            title_elem = await article_elem.query_selector(".content_block")
            if not title_elem:
                return None

            title_text = (await title_elem.inner_text()).strip()
            title_lines = [line.strip() for line in title_text.split('\n') if line.strip()]

            if len(title_lines) > 1:
                title = title_lines[-1]
            else:
                title = title_text

            if not title:
                return None

            excerpt_elem = await article_elem.query_selector(".post_excerpt")
            excerpt = ""
            if excerpt_elem:
                excerpt = (await excerpt_elem.inner_text()).strip()

            if not excerpt:
                excerpt = title

            author_info_elem = await article_elem.query_selector(".author_info")
            author = ""
            published_at = None

            if author_info_elem:
                author_info_text = (await author_info_elem.inner_text()).strip()
                author_info_lines = [line.strip() for line in author_info_text.split('\n') if line.strip()]

                if len(author_info_lines) >= 2:
                    author = author_info_lines[0]
                    date_text = author_info_lines[1]
                    published_at = self._parse_date_text(date_text)
                elif len(author_info_lines) == 1:
                    if ',' in author_info_lines[0] or len(author_info_lines[0]) < 20:
                        author = author_info_lines[0]
                    else:
                        date_text = author_info_lines[0]
                        published_at = self._parse_date_text(date_text)

            if not published_at:
                published_at = datetime.now()

            external_id = self._extract_id_from_url(url)

            return {
                "external_id": external_id,
                "title": title,
                "content": excerpt if excerpt else title,
                "summary": excerpt if excerpt else None,
                "provider": author if author else None,
                "published_at": published_at or datetime.now(),
                "url": url,
                "region": self.region,
                "category": "AI Governance",
                "language": self.language
            }
        except Exception as e:
            logger.error(f"Failed to extract article from element: {e}")
            return None

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取文章ID

        Args:
            url: 文章URL，如 https://partnershiponai.org/nightmare-on-ai-street-pais-horror-index/

        Returns:
            文章路径slug作为ID
        """
        try:
            match = re.search(r'/([^/]+)/?$', url)
            return match.group(1) if match else None
        except Exception:
            return None

    def _parse_date_text(self, date_text: str) -> datetime:
        """
        解析日期文本

        Args:
            date_text: 日期文本，如 "Oct 31, 2025"

        Returns:
            datetime对象
        """
        try:
            return datetime.strptime(date_text.strip(), '%b %d, %Y')
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

    async def _preprocess_items(self, items: List[Dict[str, Any]]) -> None:
        """
        预处理：在数据库会话外并发执行翻译和字段增强

        Args:
            items: 文章列表（会被原地修改）

        架构改进：
        - 批内串行处理（不使用asyncio.gather），避免并发过载
        - Translator内部的semaphore(2)已经控制并发
        - 单条失败不影响其他，立即记录错误
        """
        if not items:
            return

        logger.info(f"【Partnership AI】开始预处理 {len(items)} 条消息（翻译 + 字段增强）")

        # 串行处理每条消息（Translator内部有并发控制）
        for idx, item in enumerate(items, 1):
            # 提前生成message_id用于事件发布
            message_id = str(uuid.uuid4())
            item['message_id'] = message_id

            try:
                await self._preprocess_single_item(item, message_id)
                logger.debug(f"【Partnership AI】预处理完成 [{idx}/{len(items)}]: {item.get('title', '')[:30]}")
            except Exception as e:
                logger.error(f"【Partnership AI】预处理失败 [{idx}/{len(items)}]: {e}")
                # Fail Fast：失败时设置降级值，继续处理
                item['summary'] = item.get('summary', '')[:500] if item.get('summary') else ''
                item['region'] = None
                item['industry_tags'] = None
                item['ai_tag'] = None

    async def _preprocess_single_item(self, item: Dict[str, Any], message_id: str) -> None:
        """
        预处理单条消息（翻译 + 字段增强）

        Args:
            item: 文章数据（会被原地修改）
            message_id: 消息ID（用于事件发布）

        架构改进：
        - 串行执行翻译和字段增强（而非并发），降低API压力
        - 翻译失败使用降级策略，不影响字段增强
        - 详细记录每个步骤的失败信息
        """
        # 1. 翻译（单独try-catch，失败使用降级）
        try:
            summary = await self._generate_summary(item.get('summary', ''), item.get('content', ''))
            item['summary'] = summary
        except Exception as e:
            logger.error(f"【Partnership AI】翻译失败 (url={item.get('url')}): {e}")
            item['summary'] = item.get('summary', '')[:500] if item.get('summary') else ''

        # 2. 字段增强（单独try-catch，失败设为None）
        try:
            enriched = await self._enrich_fields(item.get('title', ''), item.get('content', ''), message_id)
            item['region'] = enriched.get('region')
            item['industry_tags'] = enriched.get('industry_tags')
            item['ai_tag'] = enriched.get('ai_tag')
        except Exception as e:
            logger.error(f"【Partnership AI】字段增强失败 (url={item.get('url')}): {e}")
            item['region'] = None
            item['industry_tags'] = None
            item['ai_tag'] = None

    async def _enrich_fields(self, title: str, content: str, message_id: str = None) -> Dict[str, Optional[str]]:
        """
        字段增强（region + industry_tags + ai_tag）

        Args:
            title: 标题
            content: 内容
            message_id: 消息ID（用于事件发布）

        Returns:
            包含region、industry_tags和ai_tag的字典
        """
        if not self.field_enricher:
            return {"region": None, "industry_tags": None, "ai_tag": None}

        try:
            enriched = await self.field_enricher.enrich_fields(
                title,
                content,
                message_id=message_id,
                source_name="Partnership on AI"
            )
            return enriched
        except Exception as e:
            logger.error(f"【Partnership AI】字段增强失败: {e}")
            return {"region": None, "industry_tags": None, "ai_tag": None}

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
        存储到MySQL（已经过翻译和字段增强）

        Args:
            items: 文章列表（已经过预处理）
        """
        try:
            with create_session() as db:
                for item in items:
                    message = PartnershipAIMessage(
                        id=item.get('message_id', str(uuid.uuid4())),
                        source_id=self.source_id,
                        external_id=item.get('external_id'),
                        title=item['title'],
                        content=item['content'],
                        summary=item.get('summary'),  # 使用预处理的summary
                        provider=item.get('provider'),
                        published_at=item.get('published_at'),
                        crawled_at=datetime.now(),
                        url=item['url'],
                        region=item.get('region'),
                        category=item.get('category'),
                        language=item.get('language'),
                        industry_tags=item.get('industry_tags'),  # 新增
                        ai_tag=item.get('ai_tag')  # 新增
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
        存储到ChromaDB（已经过翻译和字段增强）

        Args:
            items: 文章列表（已经过预处理）
        """
        if not self.chroma_storage or not self.embedding_client:
            return

        try:
            for item in items:
                summary = item.get('summary', '')  # 使用预处理的summary
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

        优先使用网页excerpt，无则用content。外文内容自动翻译成中文

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

        # 2. 外文内容：翻译成中文
        if self.translator:
            try:
                # 全文翻译（不截断）
                translated = await self.translator.translate(
                    source_text,
                    context="Partnership on AI博客文章摘要"
                )
                return translated
            except Exception as e:
                logger.error(f"【Partnership AI】翻译失败: {e}")
                # 降级策略：返回截断原文
                return source_text[:500] + "... [AI翻译暂不可用]"
        else:
            # 无翻译器：返回截断原文
            if len(source_text) <= 1000:
                return source_text
            return source_text[:500] + "..."

