# -*- coding: utf-8 -*-

"""
Global Center on AI Governance (GCG) Collector
南非/非洲AI治理研究中心采集器
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import Browser, Page
from sqlalchemy.exc import IntegrityError

from backend.database.entities import GCGAIMessage
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


class GCGAICollector(PlaywrightCollectorBase):
    """GCG AI治理研究中心采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - url: GCG研究页面URL
                - source_id: 消息源ID（关联message_sources表）
                - region: 地区（ZA=South Africa/Africa）
                - language: 语言（en）
        """
        super().__init__(config)
        self.interval = config.get('interval', 604800)  # 默认7天
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.url = config['config'].get('url', 'https://www.globalcenter.ai/research')
        self.region = config['config'].get('region', 'ZA')
        self.language = config['config'].get('language', 'en')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【GCG】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【GCG】LLM服务不可用，将跳过向量化和翻译")

        if _field_enricher_available:
            self.field_enricher = get_field_enricher()
        else:
            self.field_enricher = None
            logger.warning("【GCG】FieldEnricher不可用，将跳过字段增强")
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

            logger.info(f"【GCG】采集器初始化成功: {self.url}")
            return True
        except Exception as e:
            logger.error(f"【GCG】采集器初始化失败: {e}")
            return False



    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新文章URL
        2. Playwright爬取研究列表页
        3. 过滤已存在URL
        4. 访问详情页获取完整内容
        5. 并发存储到MySQL + ChromaDB
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
                logger.info(f"【GCG】开始访问 {len(new_items)} 篇文章的详情页...")
                for idx, item in enumerate(new_items, 1):
                    try:
                        full_content = await self._fetch_article_content(item['url'])
                        if full_content:
                            item['content'] = full_content
                            logger.debug(f"[{idx}/{len(new_items)}] ✓ 获取完整内容: {item['url']}")
                        else:
                            logger.debug(f"[{idx}/{len(new_items)}] ⚠ 保持使用标题: {item['url']}")
                        await asyncio.sleep(1.5)  # 详情页间隔
                    except Exception as e:
                        logger.error(f"[{idx}/{len(new_items)}] ✗ 详情页访问失败: {e}")

                await self._store_items(new_items)
                logger.info(f"【GCG】采集到 {len(new_items)} 篇新文章")
            else:
                logger.debug("【GCG】所有文章已存在，无新数据")

        except Exception as e:
            logger.error(f"【GCG】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新文章的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(GCGAIMessage).filter(
                    GCGAIMessage.source_id == self.source_id,
                    GCGAIMessage.url.isnot(None)
                ).order_by(
                    GCGAIMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL: {e}")
            return None

    async def _scrape_articles_list(self, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        Playwright爬取研究列表页，提取文章列表

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
                await asyncio.sleep(5)
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"【GCG】第 {attempt + 1} 次尝试失败: {e}，{retry_delay}秒后重试...")
                    if page:
                        await page.close()
                        page = None
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【GCG】所有重试均失败: {e}", exc_info=True)
                    if page:
                        await page.close()
                    return []

        if not page:
            return []

        try:
            # GCG使用文章列表容器
            # 根据WebFetch的信息，网站可能使用article标签或特定的class
            # 先尝试等待任何article或链接元素
            await page.wait_for_load_state("networkidle", timeout=15000)
            await asyncio.sleep(3)

            # 尝试多种选择器
            article_containers = await page.query_selector_all('article, [class*="publication"], [class*="research"], [class*="article"], [class*="card"]')

            if not article_containers:
                # 备用方案：查找包含/research/路径的链接
                logger.warning("【GCG】未找到article容器，尝试提取所有研究链接")
                research_links = await page.query_selector_all('a[href*="/research/"]')
                logger.debug(f"Found {len(research_links)} research links")
                articles_list = await self._extract_from_links(research_links, page, latest_url)
            else:
                logger.debug(f"Found {len(article_containers)} article containers")
                articles_list = await self._extract_from_containers(article_containers, latest_url)

            return articles_list

        except Exception as e:
            logger.error(f"Failed to scrape articles list: {e}", exc_info=True)
            return []
        finally:
            if page:
                await page.close()

    async def _extract_from_containers(self, containers, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        从容器元素中提取文章数据

        Args:
            containers: 文章容器元素列表
            latest_url: 最新已存储URL

        Returns:
            文章列表
        """
        articles_list = []
        for container in containers:
            try:
                article_data = await self._extract_article_from_container(container)
                if not article_data:
                    continue

                article_url = article_data.get('url')
                if not article_url:
                    continue

                if latest_url and article_url == latest_url:
                    logger.debug(f"Reached latest stored URL ({latest_url}), stopping")
                    break

                articles_list.append(article_data)
            except Exception as e:
                logger.error(f"Failed to extract from container: {e}")
                continue

        return articles_list

    async def _extract_from_links(self, links, page: Page, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        从链接列表中提取文章数据（备用方案）

        Args:
            links: 链接元素列表
            page: 页面对象
            latest_url: 最新已存储URL

        Returns:
            文章列表
        """
        articles_list = []
        seen_urls = set()

        for link_elem in links:
            try:
                href = await link_elem.get_attribute('href')
                if not href or href in seen_urls:
                    continue

                # 补全URL
                if href.startswith('/'):
                    href = f"https://www.globalcenter.ai{href}"
                elif not href.startswith('http'):
                    continue

                # 排除非研究文章
                if '/news/' in href or '/about' in href:
                    continue

                seen_urls.add(href)

                if latest_url and href == latest_url:
                    logger.debug(f"Reached latest stored URL ({latest_url}), stopping")
                    break

                # 提取标题
                title = (await link_elem.inner_text()).strip()
                if not title or len(title) < 10:
                    continue

                external_id = self._extract_id_from_url(href)

                articles_list.append({
                    "external_id": external_id,
                    "title": title,
                    "content": title,  # 初始值，后续从详情页获取
                    "summary": None,
                    "provider": None,
                    "published_at": datetime.now(),  # 初始值，从详情页获取
                    "url": href,
                    "region": self.region,
                    "category": None,
                    "language": self.language,
                    "tags": [],
                    "pdf_url": None
                })

            except Exception as e:
                logger.error(f"Failed to extract from link: {e}")
                continue

        return articles_list

    async def _extract_article_from_container(self, container) -> Optional[Dict[str, Any]]:
        """
        从文章容器元素中提取数据

        Args:
            container: 容器DOM元素

        Returns:
            文章数据字典
        """
        try:
            # 提取链接和标题
            link_elem = await container.query_selector('a[href*="/research/"]')
            if not link_elem:
                return None

            url = await link_elem.get_attribute('href')
            if url and url.startswith('/'):
                url = f"https://www.globalcenter.ai{url}"

            title_elem = await container.query_selector('h2, h3, h4, .title, [class*="title"]')
            if title_elem:
                title = (await title_elem.inner_text()).strip()
            else:
                title = (await link_elem.inner_text()).strip()

            if not url or not title:
                return None

            # 提取日期
            date_elem = await container.query_selector('time, .date, [class*="date"]')
            published_at = datetime.now()
            if date_elem:
                date_text = (await date_elem.inner_text()).strip()
                published_at = self._parse_date(date_text)

            # 提取类型
            type_elem = await container.query_selector('.type, [class*="type"], .category, [class*="category"]')
            category = None
            if type_elem:
                category = (await type_elem.inner_text()).strip()

            # 提取标签
            tag_elems = await container.query_selector_all('.tag, [class*="tag"]')
            tags = []
            for tag_elem in tag_elems:
                tag_text = (await tag_elem.inner_text()).strip()
                if tag_text:
                    tags.append(tag_text)

            external_id = self._extract_id_from_url(url)

            return {
                "external_id": external_id,
                "title": title,
                "content": title,  # 初始值，后续从详情页获取
                "summary": None,
                "provider": None,
                "published_at": published_at,
                "url": url,
                "region": self.region,
                "category": category,
                "language": self.language,
                "tags": tags,
                "pdf_url": None
            }
        except Exception as e:
            logger.error(f"Failed to extract article from container: {e}")
            return None

    async def _fetch_article_content(self, article_url: str) -> Optional[str]:
        """
        访问文章详情页，获取简介内容

        Args:
            article_url: 文章URL

        Returns:
            文章简介内容
        """
        detail_page: Optional[Page] = None
        try:
            detail_page = await self._browser.new_page()

            await detail_page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            })

            await detail_page.goto(article_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # 提取简介内容（GCG详情页通常有简短介绍）
            paragraphs = await detail_page.query_selector_all('article p, .content p, .intro p, .summary p, main p')
            content_parts = []

            for para in paragraphs:
                para_text = (await para.inner_text()).strip()
                # 只提取前几段作为简介
                if para_text and len(para_text) > 20:
                    content_parts.append(para_text)
                    # 限制字数，避免过长
                    if len('\n\n'.join(content_parts)) > 1000:
                        break

            full_content = '\n\n'.join(content_parts)
            return full_content if full_content else None

        except Exception as e:
            logger.error(f"获取文章详情失败 {article_url}: {e}")
            return None
        finally:
            if detail_page:
                await detail_page.close()

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取文章ID

        Args:
            url: 文章URL

        Returns:
            文章路径slug作为ID
        """
        try:
            match = re.search(r'/research/([^/?]+)', url)
            return match.group(1) if match else None
        except Exception:
            return None

    def _parse_date(self, date_text: str) -> datetime:
        """
        解析日期文本

        Args:
            date_text: 日期文本

        Returns:
            datetime对象
        """
        try:
            # 尝试多种日期格式
            for fmt in ['%B %d, %Y', '%b %d, %Y', '%Y-%m-%d', '%d/%m/%Y', '%B %d %Y']:
                try:
                    return datetime.strptime(date_text.strip(), fmt)
                except ValueError:
                    continue

            logger.warning(f"Failed to parse date text '{date_text}'")
            return datetime.now()
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

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        """
        并发存储到MySQL和ChromaDB

        Args:
            items: 文章列表
        """
        # 预处理：先完成翻译和字段增强（在session外）
        logger.info(f"【GCG】开始预处理 {len(items)} 条消息（翻译 + 字段增强）")

        for idx, item in enumerate(items, 1):
            # 提前生成message_id用于事件发布
            message_id = str(uuid.uuid4())
            item['message_id'] = message_id

            try:
                # 1. 翻译
                summary = await self._generate_summary(item.get('summary'), item.get('content', ''))
                item['summary'] = summary

                # 2. 字段增强
                enriched = await self._enrich_fields(item.get('title', ''), item.get('content', ''), message_id)
                item['industry_tags'] = enriched.get('industry_tags')
                item['ai_tag'] = enriched.get('ai_tag')

                logger.debug(f"【GCG】预处理完成 [{idx}/{len(items)}]: {item.get('title', '')[:30]}")
            except Exception as e:
                logger.error(f"【GCG】预处理失败 [{idx}/{len(items)}]: {e}")
                # Fail Fast：失败时设置降级值
                item['summary'] = item.get('summary', '')[:500] if item.get('summary') else ''
                item['industry_tags'] = None
                item['ai_tag'] = None

        # 串行存储到MySQL和ChromaDB
        # 注意：在Celery solo pool + nest_asyncio环境下，asyncio.gather会导致任务上下文冲突
        await self._store_to_mysql(items)
        await self._store_to_chroma(items)

    async def _enrich_fields(self, title: str, content: str, message_id: str = None) -> Dict[str, Optional[str]]:
        """
        字段增强（industry_tags + ai_tag）

        Args:
            title: 标题
            content: 内容
            message_id: 消息ID（用于事件发布）

        Returns:
            包含industry_tags和ai_tag的字典
        """
        if not self.field_enricher:
            return {"industry_tags": None, "ai_tag": None}

        try:
            enriched = await self.field_enricher.enrich_fields(
                title,
                content,
                message_id=message_id,
                source_name="GCG AI"
            )
            return {
                "industry_tags": enriched.get('industry_tags'),
                "ai_tag": enriched.get('ai_tag')
            }
        except Exception as e:
            logger.error(f"【GCG】字段增强失败: {e}")
            return {"industry_tags": None, "ai_tag": None}

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到MySQL（已经过翻译和字段增强）

        Args:
            items: 文章列表（已经过预处理）
        """
        try:
            with create_session() as db:
                for item in items:
                    message = GCGAIMessage(
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
                        tags=item.get('tags'),
                        pdf_url=item.get('pdf_url'),
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
        存储到ChromaDB

        Args:
            items: 文章列表（已包含预处理的summary）
        """
        if not self.chroma_storage or not self.embedding_client:
            return

        try:
            for idx, item in enumerate(items):
                summary = item.get('summary', '')
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

        # 3. 外文内容：翻译成中文
        if self.translator:
            try:
                # 全文翻译
                translated = await self.translator.translate(
                    source_text,
                    context="GCG AI治理研究中心文章摘要"
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

