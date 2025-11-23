# -*- coding: utf-8 -*-

"""
La Nación AI专题采集器
阿根廷主流媒体人工智能新闻采集器

数据来源：
- AI专题页面：https://www.lanacion.com.ar/tema/inteligencia-artificial-tid58563/

架构特点：
- 预翻译模式：在数据库会话外完成翻译（西班牙语→中文）
- 预增强模式：在数据库会话外完成字段增强（region + industry_tags + ai_tag）
- 详情页抓取：列表页包含标题和摘要，需访问详情页获取完整content
- 滚动加载：自动检测滚动加载机制
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import Browser, Page
from sqlalchemy.exc import IntegrityError

from backend.database.entities import LaNacionMessage
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


class LaNacionCollector(PlaywrightCollectorBase):
    """La Nación阿根廷AI专题采集器"""

    BASE_URL = 'https://www.lanacion.com.ar'
    AI_TOPIC_URL = 'https://www.lanacion.com.ar/tema/inteligencia-artificial-tid58563/'

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - config:
                    - mysql_table: MySQL表名
                    - chroma_collection: ChromaDB collection名称
                    - source_id: 消息源ID（关联message_sources表）
                    - region: 地区（阿根廷）
                    - language: 语言（es）
        """
        super().__init__(config)

        self.mysql_table = config['config']['mysql_table']
        self.chroma_collection = config['config']['chroma_collection']
        self.source_id = config.get('id', 'auto')
        self.region = config['config'].get('region', '阿根廷')
        self.language = config['config'].get('language', 'es')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【La Nación】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【La Nación】LLM服务不可用，将跳过向量化和翻译")

        if _field_enricher_available:
            self.field_enricher = get_field_enricher()
        else:
            self.field_enricher = None
            logger.warning("【La Nación】FieldEnricher不可用，将跳过字段增强")

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

            logger.info("【La Nación】采集器初始化成功")
            return True
        except Exception as e:
            logger.error(f"【La Nación】采集器初始化失败: {e}")
            return False

    async def _collect_once(self) -> None:
        """
        单次采集（流式处理架构）

        流程（Fail Fast原则）：
        1. 获取MySQL中最新文章URL
        2. 爬取列表页（滚动加载，遇到latest_url停止）
        3. 分批处理（每批10篇）
        4. 每批：访问详情页 → 翻译 → 字段增强 → 存储
        """
        try:
            latest_url = await self._get_latest_stored_url()
            logger.debug(f"【La Nación】最新存储URL: {latest_url}")

            # 爬取文章列表
            articles = await self._scrape_articles(latest_url)

            if not articles:
                logger.debug("【La Nación】没有发现新文章")
                return

            logger.info(f"【La Nación】共发现 {len(articles)} 篇新文章")

            # 分批处理（每批10篇，防止并发过载）
            batch_size = 10
            total_processed = 0

            for batch_start in range(0, len(articles), batch_size):
                batch_end = min(batch_start + batch_size, len(articles))
                batch = articles[batch_start:batch_end]

                logger.info(f"【La Nación】处理批次 [{batch_start+1}-{batch_end}/{len(articles)}]")

                # 1. 访问详情页（串行，避免反爬虫）
                for idx, item in enumerate(batch, batch_start + 1):
                    try:
                        full_content, author = await self._fetch_article_content(item['url'])
                        if full_content:
                            item['content'] = full_content
                            if author and not item.get('provider'):
                                item['provider'] = author
                            logger.debug(f"[{idx}/{len(articles)}] ✓ 详情: {item['url']}")
                        else:
                            logger.debug(f"[{idx}/{len(articles)}] ⚠ 使用摘要: {item['url']}")
                        # 延迟避免反爬虫
                        await asyncio.sleep(1.5)
                    except Exception as e:
                        logger.error(f"[{idx}/{len(articles)}] ✗ 详情页失败: {e}")

                # 2. 预处理（翻译+字段增强）
                await self._preprocess_items(batch)

                # 3. 存储（MySQL + ChromaDB）
                await self._store_items(batch)

                total_processed += len(batch)
                logger.info(f"【La Nación】批次完成，已处理 {total_processed} 篇")

                # 批次间延迟
                if batch_end < len(articles):
                    await asyncio.sleep(2)

            logger.info(f"【La Nación】采集完成，共处理 {total_processed} 篇新文章")

        except Exception as e:
            logger.error(f"【La Nación】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新文章的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(LaNacionMessage).filter(
                    LaNacionMessage.source_id == self.source_id,
                    LaNacionMessage.url.isnot(None)
                ).order_by(
                    LaNacionMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"【La Nación】获取最新URL失败: {e}")
            return None

    async def _scrape_articles(self, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        爬取文章列表（滚动加载）

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
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8',
                })

                await page.goto(self.AI_TOPIC_URL, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"【La Nación】第 {attempt + 1} 次尝试失败: {e}，{retry_delay}秒后重试...")
                    if page:
                        await page.close()
                        page = None
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【La Nación】所有重试均失败: {e}", exc_info=True)
                    if page:
                        await page.close()
                    return []

        if not page:
            return []

        try:
            # 检测文章列表容器
            selectors_to_try = [
                'article',
                '[class*="card"]',
                '[class*="item"]'
            ]

            selected_selector = None
            for selector in selectors_to_try:
                try:
                    count = await page.locator(selector).count()
                    if count > 0:
                        selected_selector = selector
                        logger.debug(f"【La Nación】使用选择器: {selector} (找到{count}个元素)")
                        break
                except Exception:
                    continue

            if not selected_selector:
                logger.warning("【La Nación】未找到文章元素")
                return []

            # 滚动加载
            articles_list = []
            scroll_attempts = 0
            max_scroll_attempts = 20
            consecutive_no_new = 0
            max_consecutive_no_new = 3

            logger.info("【La Nación】开始滚动加载...")

            while scroll_attempts < max_scroll_attempts:
                # 获取当前所有文章元素
                article_elements = await page.locator(selected_selector).all()
                current_count = len(article_elements)
                logger.debug(f"【La Nación】当前页面文章数: {current_count}")

                # 从上次结束的位置开始提取新文章
                start_index = len(articles_list)
                new_articles_in_scroll = 0

                for idx in range(start_index, current_count):
                    article_elem = article_elements[idx]
                    article_data = await self._extract_article_from_element(article_elem)

                    if not article_data:
                        continue

                    # 检查是否遇到已存储的文章
                    if latest_url and article_data['url'] == latest_url:
                        logger.info(f"【La Nación】遇到最新存储记录，停止采集：{latest_url}")
                        await page.close()
                        return articles_list

                    articles_list.append(article_data)
                    new_articles_in_scroll += 1

                if new_articles_in_scroll > 0:
                    logger.debug(f"【La Nación】本次滚动新增 {new_articles_in_scroll} 篇文章")
                    consecutive_no_new = 0
                else:
                    consecutive_no_new += 1
                    logger.debug(f"【La Nación】本次滚动无新内容 (连续{consecutive_no_new}次)")

                    if consecutive_no_new >= max_consecutive_no_new:
                        logger.info("【La Nación】连续多次无新内容，停止滚动")
                        break

                # 滚动到页面底部
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(3)  # 等待内容加载
                scroll_attempts += 1

            await page.close()
            logger.info(f"【La Nación】滚动加载完成，共获取 {len(articles_list)} 篇文章")
            return articles_list

        except Exception as e:
            logger.error(f"【La Nación】爬取文章列表失败: {e}", exc_info=True)
            if page:
                await page.close()
            return []

    async def _extract_article_from_element(self, element) -> Optional[Dict[str, Any]]:
        """
        从文章元素中提取数据

        Args:
            element: 文章DOM元素

        Returns:
            文章数据字典，失败返回None
        """
        try:
            # 提取链接（查找article元素内的第一个链接）
            link_locator = element.locator('a').first
            url = await link_locator.get_attribute('href') if await link_locator.count() > 0 else None

            if not url:
                # 备选：检查element本身是否是链接
                url = await element.get_attribute('href')

            if not url:
                return None

            # 补全相对路径
            if url.startswith('/'):
                url = f"{self.BASE_URL}{url}"

            # 提取标题
            title = None
            title_selectors = ['h3', 'h2', '[class*="text-"]']
            for selector in title_selectors:
                title_locator = element.locator(selector).first
                if await title_locator.count() > 0:
                    title = await title_locator.inner_text()
                    if title and len(title.strip()) > 10:
                        break

            if not title:
                # 备选：从链接文本提取
                title = await link_locator.inner_text() if await link_locator.count() > 0 else None

            if not title or len(title.strip()) < 10:
                return None

            title = title.strip()

            # 提取摘要（可能没有）
            summary = ''
            summary_locator = element.locator('p, [class*="description"]').first
            if await summary_locator.count() > 0:
                summary = await summary_locator.inner_text()
                summary = summary.strip() if summary else ''

            # 提取日期
            date_text = await element.inner_text()
            published_at = self._parse_date(date_text)

            # 生成external_id（从URL提取）
            external_id = self._extract_id_from_url(url)

            return {
                'external_id': external_id,
                'title': title,
                'url': url,
                'summary': summary,
                'content': summary,  # 暂用摘要，详情页会替换
                'provider': None,
                'published_at': published_at,
            }

        except Exception as e:
            logger.debug(f"【La Nación】提取文章数据失败: {e}")
            return None

    def _extract_id_from_url(self, url: str) -> str:
        """
        从URL中提取文章ID

        例如：https://www.lanacion.com.ar/tecnologia/...-nid12345/ → nid12345
        """
        match = re.search(r'-nid(\d+)/?$', url)
        if match:
            return f"nid{match.group(1)}"

        # 备选：使用URL最后一段
        parts = url.rstrip('/').split('/')
        return parts[-1] if parts else str(uuid.uuid4())

    def _parse_date(self, date_text: str) -> datetime:
        """
        解析西班牙语日期

        例如："21 de noviembre de 2024"
        """
        try:
            # 西班牙语月份映射
            months = {
                'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
                'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
                'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
            }

            # 匹配 "日 de 月 de 年" 格式
            match = re.search(r'(\d+)\s+de\s+(\w+)\s+de\s+(\d{4})', date_text)
            if match:
                day = int(match.group(1))
                month_name = match.group(2).lower()
                year = int(match.group(3))

                month = months.get(month_name)
                if month:
                    return datetime(year, month, day)

        except Exception as e:
            logger.debug(f"【La Nación】日期解析失败: {e}")

        # 降级：返回当前时间
        return datetime.now()

    async def _fetch_article_content(self, url: str) -> tuple[Optional[str], Optional[str]]:
        """
        访问详情页获取完整内容

        Args:
            url: 文章URL

        Returns:
            (完整内容, 作者)，失败返回(None, None)
        """
        page: Optional[Page] = None
        try:
            page = await self._browser.new_page()

            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8',
                'Referer': self.AI_TOPIC_URL,
            })

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # 提取正文内容
            content_selectors = [
                'article [class*="content"]',
                'article [class*="body"]',
                '[class*="article-body"]',
                'article p',
            ]

            content_paragraphs = []
            for selector in content_selectors:
                try:
                    paragraphs = await page.locator(selector).all()
                    if paragraphs:
                        for p in paragraphs:
                            text = await p.inner_text()
                            if text and len(text.strip()) > 20:
                                content_paragraphs.append(text.strip())
                        if content_paragraphs:
                            break
                except Exception:
                    continue

            # 提取作者
            author = None
            author_selectors = [
                '[class*="author"]',
                '[class*="byline"]',
                'a[rel="author"]'
            ]

            for selector in author_selectors:
                try:
                    author_elem = await page.query_selector(selector)
                    if author_elem:
                        author_text = await author_elem.inner_text()
                        if author_text:
                            # 清理 "Por XXX" 格式
                            author = re.sub(r'^Por\s+', '', author_text.strip())
                            break
                except Exception:
                    continue

            await page.close()

            if content_paragraphs:
                full_content = '\n\n'.join(content_paragraphs)
                return full_content, author

            return None, None

        except Exception as e:
            logger.debug(f"【La Nación】详情页访问失败: {e}")
            if page:
                await page.close()
            return None, None

    async def _preprocess_items(self, items: List[Dict[str, Any]]) -> None:
        """
        预处理文章列表（翻译+字段增强）

        Args:
            items: 文章列表（原地修改）
        """
        for item in items:
            # 生成message_id
            message_id = str(uuid.uuid4())
            item['message_id'] = message_id

            # 翻译
            await self._translate_item(item)

            # 字段增强
            await self._enrich_fields(item, message_id)

    async def _translate_item(self, item: Dict[str, Any]) -> None:
        """
        翻译单篇文章（西班牙语→中文）

        Args:
            item: 文章数据（原地修改）
        """
        if not self.translator:
            return

        try:
            # 翻译标题
            if item.get('title'):
                translated_title = await self.translator.translate(
                    item['title'],
                    context="新闻标题",
                    source_lang="es",
                    target_lang="zh"
                )
                item['title'] = translated_title

            # 翻译内容
            if item.get('content'):
                translated_content = await self.translator.translate(
                    item['content'],
                    context="新闻正文",
                    source_lang="es",
                    target_lang="zh"
                )
                item['content'] = translated_content

            # 翻译摘要
            if item.get('summary') and item['summary'] != item['content']:
                translated_summary = await self.translator.translate(
                    item['summary'],
                    context="新闻摘要",
                    source_lang="es",
                    target_lang="zh"
                )
                item['summary'] = translated_summary
            elif not item.get('summary'):
                # 如果没有摘要，使用翻译后的content前1000字
                item['summary'] = item['content'][:1000] if len(item['content']) > 1000 else item['content']

        except Exception as e:
            logger.error(f"【La Nación】翻译失败: {e}")
            # 降级：保持原文

    async def _enrich_fields(self, item: Dict[str, Any], message_id: str) -> None:
        """
        增强字段（region + industry_tags + ai_tag）

        Args:
            item: 文章数据（原地修改）
            message_id: 消息ID（用于事件发布）
        """
        if not self.field_enricher:
            item['region'] = self.region
            item['industry_tags'] = None
            item['ai_tag'] = None
            return

        try:
            enriched = await self.field_enricher.enrich_fields(
                title=item['title'],
                content=item['content'],
                message_id=message_id
            )
            item['region'] = enriched.get('region', self.region)
            item['industry_tags'] = enriched.get('industry_tags')
            item['ai_tag'] = enriched.get('ai_tag')

        except Exception as e:
            logger.error(f"【La Nación】字段增强失败: {e}")
            item['region'] = self.region
            item['industry_tags'] = None
            item['ai_tag'] = None

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        """
        存储文章到MySQL和ChromaDB

        Args:
            items: 文章列表
        """
        # 并发存储
        await asyncio.gather(
            self._store_to_mysql(items),
            self._store_to_chroma(items),
            return_exceptions=True
        )

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到MySQL

        Args:
            items: 文章列表
        """
        stored_count = 0
        duplicate_count = 0

        for item in items:
            try:
                with create_session() as db:
                    message = LaNacionMessage(
                        id=item['message_id'],
                        source_id=self.source_id,
                        external_id=item['external_id'],
                        title=item['title'],
                        content=item['content'],
                        summary=item['summary'],
                        provider=item.get('provider'),
                        published_at=item['published_at'],
                        crawled_at=datetime.now(),
                        url=item['url'],
                        region=item.get('region'),
                        language=self.language,
                        industry_tags=item.get('industry_tags'),
                        ai_tag=item.get('ai_tag'),
                    )

                    db.add(message)
                    db.commit()
                    stored_count += 1

            except IntegrityError:
                duplicate_count += 1
                logger.debug(f"【La Nación】重复记录（跳过）: {item['url']}")
            except Exception as e:
                logger.error(f"【La Nación】MySQL存储失败: {e}")

        if stored_count > 0:
            logger.info(f"【La Nación】MySQL存储完成: {stored_count} 篇新增, {duplicate_count} 篇重复")

    async def _store_to_chroma(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到ChromaDB

        Args:
            items: 文章列表
        """
        if not self.chroma_storage or not self.embedding_client:
            return

        try:
            if not self.chroma_storage.is_initialized():
                logger.warning("【La Nación】ChromaDB未初始化，跳过向量存储")
                return

            # 准备向量化数据
            ids = []
            documents = []
            metadatas = []

            for item in items:
                # 使用message_id作为向量ID（稳定且唯一）
                ids.append(item['message_id'])

                # 组合标题和内容用于向量化
                doc_text = f"{item['title']}\n\n{item['content']}"
                documents.append(doc_text)

                # 元数据
                metadatas.append({
                    'id': item['message_id'],
                    'source_id': self.source_id,
                    'external_id': item['external_id'],
                    'title': item['title'],
                    'summary': item.get('summary', '')[:500],
                    'published_at': item['published_at'].isoformat() if item['published_at'] else '',
                    'url': item['url'],
                    'region': item.get('region', ''),
                    'language': self.language,
                })

            if not ids:
                return

            # 生成嵌入向量
            embeddings = await self.embedding_client.get_embeddings(documents)

            if not embeddings:
                logger.warning("【La Nación】嵌入向量生成失败")
                return

            # 批量存储（每批50条）
            batch_size = 50
            stored_count = 0

            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i + batch_size]
                batch_embeddings = embeddings[i:i + batch_size]
                batch_documents = documents[i:i + batch_size]
                batch_metadatas = metadatas[i:i + batch_size]

                self.chroma_storage.upsert(
                    collection_name=self.chroma_collection,
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    documents=batch_documents,
                    metadatas=batch_metadatas
                )

                stored_count += len(batch_ids)

            logger.info(f"【La Nación】ChromaDB存储完成: {stored_count} 条")

        except Exception as e:
            logger.error(f"【La Nación】ChromaDB存储失败: {e}")
