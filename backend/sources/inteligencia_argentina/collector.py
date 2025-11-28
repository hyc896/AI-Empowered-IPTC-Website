# -*- coding: utf-8 -*-

"""
Inteligencia Argentina Collector
阿根廷情报与分析网站AI专栏采集器

数据来源：
- AI分类：https://inteligenciaargentina.ar/categoria/inteligencia-artificial

架构特点：
- 继承PlaywrightCollectorBase基类
- 预翻译模式：在数据库会话外完成翻译
- 预增强模式：在数据库会话外完成字段增强（region + industry_tags + ai_tag）
- 分页采集：支持多页加载，遇到latest_url停止
- 详情页抓取：列表页只有简短摘要，需访问详情页获取完整content
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import Page
from sqlalchemy.exc import IntegrityError

from backend.database.entities import InteligenciaArgentinaMessage
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


class InteligenciaArgentinaCollector(PlaywrightCollectorBase):
    """阿根廷情报与分析网站AI专栏采集器"""

    BASE_URL = "https://inteligenciaargentina.ar/categoria/inteligencia-artificial"

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - id: 消息源ID
                - config:
                    - interval: 采集间隔（秒）
                    - mysql_table: MySQL表名
                    - chroma_collection: ChromaDB collection名称
                    - region: 地区（阿根廷）
                    - language: 语言（es=西班牙语）
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
            logger.warning("【InteligenciaArgentina】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【InteligenciaArgentina】LLM服务不可用，将跳过向量化和翻译")

        if _field_enricher_available:
            self.field_enricher = get_field_enricher()
        else:
            self.field_enricher = None
            logger.warning("【InteligenciaArgentina】FieldEnricher不可用，将跳过字段增强")

        # 增强反检测配置
        self.browser_args.extend([
            '--disable-blink-features=AutomationControlled',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ])

        logger.info(f"【InteligenciaArgentina】采集器初始化完成（source_id={self.source_id}, interval={self.interval}s）")

    async def _on_initialize(self) -> bool:
        """
        可选的初始化钩子

        Returns:
            bool: 初始化成功返回True，失败返回False
        """
        if self.chroma_storage and not self.chroma_storage.is_initialized():
            logger.warning("【InteligenciaArgentina】ChromaDB未初始化，将只存储到MySQL")
            self.chroma_storage = None

        return True

    async def _collect_once(self) -> None:
        """
        单次采集（三阶段架构）

        流程：
        1. Scraping阶段：获取MySQL中最新文章URL，逐页抓取直到遇到该URL
        2. Processing阶段：在数据库会话外完成翻译和字段增强
        3. Storing阶段：批量写入MySQL和ChromaDB
        """
        try:
            latest_url = await self._get_latest_stored_url()
            logger.info(f"【InteligenciaArgentina】开始采集，最新已存储URL: {latest_url or '无（首次采集）'}")

            # Scraping阶段
            items = await self._scrape_articles(latest_url)
            if not items:
                logger.info("【InteligenciaArgentina】未发现新文章")
                return

            logger.info(f"【InteligenciaArgentina】抓取到 {len(items)} 篇新文章")

            # Processing阶段（在数据库会话外执行）
            await self._preprocess_items(items)

            # Storing阶段
            await self._store_items(items)

            logger.info(f"【InteligenciaArgentina】采集完成，共处理 {len(items)} 篇文章")

        except Exception as e:
            logger.error(f"【InteligenciaArgentina】采集失败: {e}", exc_info=True)
            raise

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取数据库中最新存储的文章URL

        Returns:
            最新URL，如果数据库为空则返回None
        """
        try:
            with create_session() as db:
                latest = db.query(InteligenciaArgentinaMessage.url) \
                    .filter(InteligenciaArgentinaMessage.source_id == self.source_id) \
                    .order_by(InteligenciaArgentinaMessage.crawled_at.desc()) \
                    .first()

                return latest[0] if latest else None
        except Exception as e:
            logger.error(f"【InteligenciaArgentina】查询最新URL失败: {e}")
            return None

    async def _scrape_articles(self, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        Scraping阶段：从最后一页向前抓取文章列表和详情页

        注意：该网站文章按时间升序排列（第1页最老，最后一页最新），
        因此需要从最后一页开始向前采集，遇到已存储URL时停止。

        Args:
            latest_url: 最新已存储的URL，遇到该URL停止

        Returns:
            文章字典列表
        """
        page = await self._browser.new_page()
        items = []

        try:
            # 第一步：获取总页数
            total_pages = await self._get_total_pages(page)
            logger.info(f"【InteligenciaArgentina】网站共 {total_pages} 页，从最后一页开始采集")

            # 第二步：从最后一页向前采集
            current_page = total_pages

            while current_page >= 1:
                if current_page == 1:
                    url = self.BASE_URL
                else:
                    url = f"{self.BASE_URL}?page={current_page}"

                logger.info(f"【InteligenciaArgentina】正在抓取第 {current_page} 页: {url}")

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)  # 等待内容渲染
                except Exception as e:
                    logger.warning(f"【InteligenciaArgentina】第 {current_page} 页加载失败: {e}")
                    current_page -= 1
                    continue

                # 提取文章链接（<a>标签包含<h3>）
                article_links = await page.query_selector_all('a:has(h3)')

                if not article_links:
                    logger.info(f"【InteligenciaArgentina】第 {current_page} 页无文章")
                    current_page -= 1
                    continue

                logger.info(f"【InteligenciaArgentina】第 {current_page} 页找到 {len(article_links)} 篇文章")

                page_stopped = False
                page_items = []  # 当前页的文章

                for link in article_links:
                    try:
                        article_url = await link.get_attribute('href')
                        if not article_url:
                            continue

                        # 确保是完整URL
                        if not article_url.startswith('http'):
                            article_url = f"https://inteligenciaargentina.ar{article_url}"

                        # 遇到已存储URL，停止当前页后续文章采集
                        if latest_url and article_url == latest_url:
                            logger.info(f"【InteligenciaArgentina】遇到最新已存储URL，停止采集")
                            page_stopped = True
                            break

                        # 提取列表页信息
                        title_elem = await link.query_selector('h3')
                        title = await title_elem.inner_text() if title_elem else ''

                        # 日期在 span.autor-y-fecha 中（格式：DD/MM/YYYY）
                        date_elem = await link.query_selector('span.autor-y-fecha')
                        date_text = await date_elem.inner_text() if date_elem else ''

                        # 摘要在 span.listado-llamada 中
                        excerpt_elem = await link.query_selector('span.listado-llamada')
                        excerpt = await excerpt_elem.inner_text() if excerpt_elem else ''

                        # 解析日期（DD/MM/YYYY）
                        published_at = self._parse_date(date_text)

                        # 提取external_id（URL slug）
                        external_id = self._extract_slug(article_url)

                        page_items.append({
                            'url': article_url,
                            'title': title.strip(),
                            'excerpt': excerpt.strip(),
                            'published_at': published_at,
                            'external_id': external_id,
                        })

                    except Exception as e:
                        logger.warning(f"【InteligenciaArgentina】提取文章信息失败: {e}")
                        continue

                # 将当前页文章添加到总列表（保持时间降序，最新的在前）
                items.extend(page_items)

                if page_stopped:
                    break

                current_page -= 1

            # 访问详情页获取完整content
            if items:
                logger.info(f"【InteligenciaArgentina】开始访问 {len(items)} 篇详情页")
                await self._fetch_article_contents(page, items)

        finally:
            await page.close()

        return items

    async def _get_total_pages(self, page: Page) -> int:
        """
        获取网站总页数

        Args:
            page: Playwright页面对象

        Returns:
            总页数
        """
        try:
            await page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # 查找分页链接，提取最大页码
            pagination_links = await page.query_selector_all('a[href*="?page="]')
            max_page = 1

            for link in pagination_links:
                href = await link.get_attribute('href')
                if href:
                    import re
                    match = re.search(r'\?page=(\d+)', href)
                    if match:
                        page_num = int(match.group(1))
                        max_page = max(max_page, page_num)

            return max_page

        except Exception as e:
            logger.warning(f"【InteligenciaArgentina】获取总页数失败: {e}，使用默认值10")
            return 10

    async def _fetch_article_contents(self, page: Page, items: List[Dict[str, Any]]) -> None:
        """
        访问详情页获取完整content

        Args:
            page: Playwright页面对象
            items: 文章列表（会被原地修改，添加content字段）
        """
        # 设置更真实的User-Agent和浏览器上下文
        context = page.context
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['es-AR', 'es', 'en']});
        """)

        for idx, item in enumerate(items, 1):
            try:
                logger.debug(f"【InteligenciaArgentina】访问详情页 {idx}/{len(items)}: {item['url']}")

                # 使用networkidle等待，确保JavaScript完全执行
                await page.goto(item['url'], wait_until="networkidle", timeout=60000)
                await asyncio.sleep(2)  # 增加延迟，避免触发反爬虫

                # 提取文章正文（实际在div.contenido中）
                content_elem = await page.query_selector('div.contenido') or \
                              await page.query_selector('article') or \
                              await page.query_selector('main')

                if content_elem:
                    # 移除导航、广告等元素
                    selectors_to_remove = ['nav', 'header', 'footer', '.advertisement', '.sidebar', 'script', 'style']
                    for selector in selectors_to_remove:
                        try:
                            elements = await content_elem.query_selector_all(selector)
                            for elem in elements:
                                await elem.evaluate('node => node.remove()')
                        except Exception:
                            pass

                    content = await content_elem.inner_text()
                    item['content'] = content.strip()
                    logger.debug(f"【InteligenciaArgentina】成功提取正文 {len(item['content'])} 字符")
                else:
                    logger.warning(f"【InteligenciaArgentina】未找到正文内容: {item['url']}")
                    item['content'] = item['excerpt'] or item['title']

                # 提取作者（通常在meta标签或byline中）
                author_elem = await page.query_selector('meta[name="author"]') or \
                             await page.query_selector('.author') or \
                             await page.query_selector('.byline')

                if author_elem:
                    if await author_elem.get_attribute('content'):
                        item['provider'] = await author_elem.get_attribute('content')
                    else:
                        item['provider'] = await author_elem.inner_text()
                else:
                    item['provider'] = None

            except Exception as e:
                logger.warning(f"【InteligenciaArgentina】详情页访问失败 {item['url']}: {e}")
                # 降级策略：使用摘要作为content
                item['content'] = item.get('excerpt') or item['title']
                item['provider'] = None

    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """
        解析日期字符串（DD/MM/YYYY）

        Args:
            date_text: 日期字符串

        Returns:
            datetime对象，解析失败返回None
        """
        try:
            # 提取DD/MM/YYYY格式
            match = re.search(r'(\d{2})/(\d{2})/(\d{4})', date_text)
            if match:
                day, month, year = match.groups()
                return datetime(int(year), int(month), int(day))
        except Exception as e:
            logger.warning(f"【InteligenciaArgentina】日期解析失败: {date_text}, {e}")

        return None

    def _extract_slug(self, url: str) -> str:
        """
        从URL提取slug作为external_id

        Args:
            url: 文章URL

        Returns:
            slug字符串
        """
        try:
            # https://inteligenciaargentina.ar/inteligencia-artificial/brasil-decime-que-se-siente-fabricar-chip
            parts = url.rstrip('/').split('/')
            if len(parts) >= 2:
                return parts[-1]  # 取最后一段作为slug
        except Exception as e:
            logger.warning(f"【InteligenciaArgentina】提取slug失败: {url}, {e}")

        return url  # 降级：使用完整URL

    async def _preprocess_items(self, items: List[Dict[str, Any]]) -> None:
        """
        Processing阶段：在数据库会话外并发执行翻译和字段增强

        Args:
            items: 文章列表（会被原地修改）
        """
        if not items:
            return

        logger.info(f"【InteligenciaArgentina】开始预处理 {len(items)} 条消息（翻译 + 字段增强）")

        for idx, item in enumerate(items, 1):
            # 生成message_id用于事件发布
            message_id = str(uuid.uuid4())
            item['message_id'] = message_id

            try:
                await self._preprocess_single_item(item, idx, len(items))
            except Exception as e:
                logger.error(f"【InteligenciaArgentina】预处理失败 [{idx}/{len(items)}]: {e}", exc_info=True)
                # 设置降级字段
                item['summary'] = item.get('content', '')[:500] if item.get('content') else item['title']
                item['region'] = self.region
                item['industry_tags'] = '人工智能'
                item['ai_tag'] = 'AI产业信息'

    async def _preprocess_single_item(self, item: Dict[str, Any], idx: int, total: int) -> None:
        """
        预处理单条消息

        Args:
            item: 消息字典（会被原地修改）
            idx: 当前索引（用于日志）
            total: 总数（用于日志）
        """
        logger.debug(f"【InteligenciaArgentina】预处理 [{idx}/{total}]: {item['title']}")

        # 1. 翻译content生成中文summary（西班牙语→中文）
        if self.translator and item.get('content'):
            try:
                translated_summary = await self.translator.translate(
                    item['content'],
                    context="阿根廷AI新闻摘要",
                    source_lang="es",
                    target_lang="zh"
                )
                item['summary'] = translated_summary
            except Exception as e:
                logger.warning(f"【InteligenciaArgentina】翻译失败 [{idx}/{total}]: {e}")
                # 降级：使用原文前500字
                item['summary'] = item['content'][:500]
        else:
            item['summary'] = item.get('content', '')[:500] or item['title']

        # 2. 字段增强（region + industry_tags + ai_tag）
        if self.field_enricher:
            try:
                enriched = await self.field_enricher.enrich_fields(
                    title=item['title'],
                    content=item.get('content', ''),
                    message_id=item['message_id']
                )
                item['region'] = enriched.get('region') or self.region
                item['industry_tags'] = enriched.get('industry_tags') or '人工智能'
                item['ai_tag'] = enriched.get('ai_tag') or 'AI产业信息'
            except Exception as e:
                logger.warning(f"【InteligenciaArgentina】字段增强失败 [{idx}/{total}]: {e}")
                # 降级
                item['region'] = self.region
                item['industry_tags'] = '人工智能'
                item['ai_tag'] = 'AI产业信息'
        else:
            # 默认值
            item['region'] = self.region
            item['industry_tags'] = '人工智能'
            item['ai_tag'] = 'AI产业信息'

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        """
        Storing阶段：串行写入MySQL和ChromaDB

        注意：在Celery solo pool + nest_asyncio环境下，asyncio.gather会导致任务上下文冲突
        改为串行执行以保证稳定性

        Args:
            items: 预处理后的文章列表
        """
        if not items:
            return

        # 串行写入MySQL和ChromaDB
        try:
            await self._store_to_mysql(items)
        except Exception as e:
            logger.error(f"【InteligenciaArgentina】MySQL存储失败: {e}", exc_info=True)

        try:
            await self._store_to_chroma(items)
        except Exception as e:
            logger.error(f"【InteligenciaArgentina】ChromaDB存储失败: {e}", exc_info=True)

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> int:
        """
        存储到MySQL

        Args:
            items: 文章列表

        Returns:
            成功插入的记录数
        """
        stored_count = 0

        with create_session() as db:
            for item in items:
                try:
                    message = InteligenciaArgentinaMessage(
                        id=item['message_id'],
                        source_id=self.source_id,
                        external_id=item.get('external_id'),
                        title=item['title'],
                        content=item.get('content', item['title']),
                        summary=item.get('summary'),
                        provider=item.get('provider'),
                        published_at=item.get('published_at'),
                        crawled_at=datetime.now(),
                        url=item['url'],
                        region=item.get('region'),
                        industry_tags=item.get('industry_tags'),
                        ai_tag=item.get('ai_tag'),
                        category='inteligencia-artificial',
                        language=self.language,
                        excerpt=item.get('excerpt'),
                    )

                    db.add(message)
                    db.commit()
                    stored_count += 1

                except IntegrityError:
                    db.rollback()
                    logger.debug(f"【InteligenciaArgentina】URL已存在，跳过: {item['url']}")
                except Exception as e:
                    db.rollback()
                    logger.error(f"【InteligenciaArgentina】MySQL插入失败: {item['url']}, {e}")

        logger.info(f"【InteligenciaArgentina】MySQL存储完成: {stored_count}/{len(items)}")
        return stored_count

    async def _store_to_chroma(self, items: List[Dict[str, Any]]) -> int:
        """
        存储到ChromaDB

        Args:
            items: 文章列表

        Returns:
            成功插入的记录数
        """
        if not self.chroma_storage or not self.embedding_client:
            logger.debug("【InteligenciaArgentina】跳过ChromaDB存储（未配置）")
            return 0

        try:
            # 准备向量化数据
            texts = []
            metadatas = []
            ids = []

            for item in items:
                # 使用中文summary进行向量化（翻译后）
                text = item.get('summary') or item.get('content', '')[:1000]
                if not text:
                    continue

                texts.append(text)
                metadatas.append({
                    'id': item['message_id'],
                    'source_id': self.source_id,
                    'title': item['title'],
                    'summary': item.get('summary', ''),
                    'published_at': item['published_at'].isoformat() if item.get('published_at') else '',
                    'url': item['url'],
                    'region': item.get('region', ''),
                    'industry_tags': item.get('industry_tags', ''),
                    'ai_tag': item.get('ai_tag', ''),
                })
                # 使用message_id作为ChromaDB ID（确保一致性）
                ids.append(item['message_id'])

            if not texts:
                logger.warning("【InteligenciaArgentina】无有效文本进行向量化")
                return 0

            # 批量向量化
            embeddings = await self.embedding_client.embed_batch(texts)

            # 批量插入ChromaDB
            self.chroma_storage.upsert(
                collection_name=self.chroma_collection,
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=texts
            )

            logger.info(f"【InteligenciaArgentina】ChromaDB存储完成: {len(ids)}/{len(items)}")
            return len(ids)

        except Exception as e:
            logger.error(f"【InteligenciaArgentina】ChromaDB存储失败: {e}", exc_info=True)
            raise
