# -*- coding: utf-8 -*-

"""
VentureBeat Collector
VentureBeat科技媒体采集器（美国AI、数据基础设施、安全领域新闻）

数据来源：
- AI栏目：https://venturebeat.com/category/ai
- 数据基础设施栏目：https://venturebeat.com/category/data-infrastructure
- 安全栏目：https://venturebeat.com/category/security

架构特点：
- 多栏目采集：统一逻辑处理3个栏目
- 预翻译模式：在数据库会话外完成翻译
- 预增强模式：在数据库会话外完成字段增强（region + industry_tags）
- 详情页抓取：列表页只有excerpt，需访问详情页获取完整content
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright
from sqlalchemy.exc import IntegrityError

from backend.database.entities import VentureBeatMessage
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


class VentureBeatCollector:
    """VentureBeat科技媒体采集器"""

    # 支持的栏目配置
    CATEGORIES = {
        'ai': {
            'name': 'AI',
            'url': 'https://venturebeat.com/category/ai/',
            'display': 'AI'
        },
        'data-infrastructure': {
            'name': 'Data Infrastructure',
            'url': 'https://venturebeat.com/category/data-infrastructure/',
            'display': 'Data Infrastructure'
        },
        'security': {
            'name': 'Security',
            'url': 'https://venturebeat.com/category/security/',
            'display': 'Security'
        }
    }

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - categories: 要采集的栏目列表（默认全部）
                - source_id: 消息源ID（关联message_sources表）
                - region: 地区（US=United States 美国）
                - language: 语言（en）
        """
        self.config = config
        self.interval = config.get('interval', 86400)  # 默认每天一次
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.source_id = config.get('id', 'auto')
        self.region = config['config'].get('region', 'US')
        self.language = config['config'].get('language', 'en')

        # 要采集的栏目（默认全部）
        self.enabled_categories = config['config'].get('categories', ['ai', 'data-infrastructure', 'security'])

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【VentureBeat】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【VentureBeat】LLM服务不可用，将跳过向量化和翻译")

        if _field_enricher_available:
            self.field_enricher = get_field_enricher()
        else:
            self.field_enricher = None
            logger.warning("【VentureBeat】FieldEnricher不可用，将跳过字段增强")

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

            logger.info(f"【VentureBeat】采集器初始化成功（栏目: {', '.join(self.enabled_categories)}）")
            return True
        except Exception as e:
            logger.error(f"【VentureBeat】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【VentureBeat】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【VentureBeat】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【VentureBeat】采集失败: {e}")

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        await self._close_browser()
        logger.info("【VentureBeat】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新文章URL
        2. 遍历所有启用的栏目
        3. Playwright爬取列表页
        4. 过滤已存在URL
        5. 访问详情页获取完整内容
        6. 并发翻译和字段增强（在数据库会话外）
        7. 存储到MySQL + ChromaDB
        """
        try:
            latest_url = await self._get_latest_stored_url()
            logger.debug(f"【VentureBeat】Latest stored URL: {latest_url}")

            all_articles = []

            # 遍历所有栏目
            for category_key in self.enabled_categories:
                category_config = self.CATEGORIES.get(category_key)
                if not category_config:
                    logger.warning(f"【VentureBeat】未知栏目: {category_key}")
                    continue

                logger.info(f"【VentureBeat】开始采集栏目: {category_config['display']}")
                articles = await self._scrape_category(category_config, latest_url)
                all_articles.extend(articles)

            if not all_articles:
                logger.debug("【VentureBeat】没有发现新文章")
                return

            # 访问详情页获取完整content
            logger.info(f"【VentureBeat】开始访问 {len(all_articles)} 篇文章的详情页...")
            for idx, item in enumerate(all_articles, 1):
                try:
                    full_content, author = await self._fetch_article_content(item['url'])
                    if full_content:
                        item['content'] = full_content
                        if author and not item.get('provider'):
                            item['provider'] = author
                        logger.debug(f"[{idx}/{len(all_articles)}] ✓ 获取完整内容: {item['url']}")
                    else:
                        logger.debug(f"[{idx}/{len(all_articles)}] ⚠ 保持使用摘要: {item['url']}")
                    # 添加延迟避免触发反爬虫
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"[{idx}/{len(all_articles)}] ✗ 详情页访问失败: {e}")

            # 预处理：并发执行翻译和字段增强（在数据库会话外）
            await self._preprocess_items(all_articles)

            # 存储
            await self._store_items(all_articles)
            logger.info(f"【VentureBeat】采集到 {len(all_articles)} 篇新文章")

        except Exception as e:
            logger.error(f"【VentureBeat】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新文章的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(VentureBeatMessage).filter(
                    VentureBeatMessage.source_id == self.source_id,
                    VentureBeatMessage.url.isnot(None)
                ).order_by(
                    VentureBeatMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"【VentureBeat】Failed to get latest URL: {e}")
            return None

    async def _scrape_category(
        self,
        category_config: Dict[str, str],
        latest_url: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        爬取单个栏目的文章列表

        Args:
            category_config: 栏目配置
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

                await page.goto(category_config['url'], wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"【VentureBeat】第 {attempt + 1} 次尝试失败: {e}，{retry_delay}秒后重试...")
                    if page:
                        await page.close()
                        page = None
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【VentureBeat】所有重试均失败: {e}", exc_info=True)
                    if page:
                        await page.close()
                    return []

        if not page:
            return []

        try:
            # VentureBeat通常使用article标签或.post类
            # 尝试多种常见选择器
            selectors_to_try = [
                'article',
                '.post',
                '[class*="article"]',
                '[class*="post-item"]'
            ]

            article_elements = []
            for selector in selectors_to_try:
                try:
                    await page.wait_for_selector(selector, timeout=10000)
                    article_elements = await page.query_selector_all(selector)
                    if article_elements:
                        logger.debug(f"【VentureBeat】找到 {len(article_elements)} 篇文章（使用选择器: {selector}）")
                        break
                except Exception:
                    continue

            if not article_elements:
                logger.warning(f"【VentureBeat】未找到文章元素（栏目: {category_config['name']}）")
                return []

            articles_list = []
            for article_elem in article_elements:
                article_data = await self._extract_article_from_element(article_elem, category_config['name'])

                if not article_data:
                    continue

                article_url = article_data.get('url')
                if not article_url:
                    continue

                # 遇到已存在URL立即停止
                if latest_url and article_url == latest_url:
                    logger.debug(f"【VentureBeat】Reached latest stored URL ({latest_url}), stopping")
                    break

                articles_list.append(article_data)

            return articles_list

        except Exception as e:
            logger.error(f"【VentureBeat】Failed to scrape category {category_config['name']}: {e}", exc_info=True)
            return []
        finally:
            if page:
                await page.close()

    async def _extract_article_from_element(
        self,
        article_elem,
        category: str
    ) -> Optional[Dict[str, Any]]:
        """
        从article元素中提取文章数据

        Args:
            article_elem: article DOM元素
            category: 栏目名称

        Returns:
            文章数据字典
        """
        try:
            # 提取标题和URL
            title_elem = await article_elem.query_selector('h2 a, h3 a, .entry-title a, [class*="title"] a')
            if not title_elem:
                return None

            url = await title_elem.get_attribute('href')
            title = (await title_elem.inner_text()).strip()

            if not url or not title:
                return None

            # 确保URL是完整的
            if not url.startswith('http'):
                url = f"https://venturebeat.com{url}"

            # 提取摘要/excerpt
            excerpt_elem = await article_elem.query_selector('.excerpt, [class*="excerpt"], [class*="summary"], p')
            excerpt = ""
            if excerpt_elem:
                excerpt = (await excerpt_elem.inner_text()).strip()

            # 提取发布时间
            time_elem = await article_elem.query_selector('time, .date, [class*="date"], [class*="time"]')
            published_at = datetime.now()
            if time_elem:
                datetime_attr = await time_elem.get_attribute('datetime')
                if datetime_attr:
                    published_at = self._parse_datetime(datetime_attr)
                else:
                    time_text = (await time_elem.inner_text()).strip()
                    published_at = self._parse_datetime(time_text)

            # 提取作者
            author_elem = await article_elem.query_selector('.author, [class*="author"], [rel="author"]')
            provider = None
            if author_elem:
                provider = (await author_elem.inner_text()).strip()

            # 提取特色图片
            img_elem = await article_elem.query_selector('img')
            featured_image = None
            if img_elem:
                featured_image = await img_elem.get_attribute('src')

            external_id = self._extract_id_from_url(url)

            return {
                "external_id": external_id,
                "title": title,
                "content": excerpt if excerpt else title,  # 列表页的content是excerpt，后续访问详情页获取完整内容
                "excerpt": excerpt,
                "provider": provider,
                "published_at": published_at,
                "url": url,
                "category": category,
                "language": self.language,
                "featured_image": featured_image,
                "region": None,  # 将由field_enricher填充
                "industry_tags": None  # 将由field_enricher填充
            }
        except Exception as e:
            logger.error(f"【VentureBeat】Failed to extract article: {e}")
            return None

    async def _fetch_article_content(self, article_url: str) -> tuple[Optional[str], Optional[str]]:
        """
        访问文章详情页，获取完整内容和作者

        Args:
            article_url: 文章URL

        Returns:
            (完整的文章内容, 作者名)
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

            # 提取作者信息
            author = None
            author_elem = await detail_page.query_selector('.author-name, [rel="author"], [class*="author"]')
            if author_elem:
                author = (await author_elem.inner_text()).strip()

            # 提取文章正文内容
            # VentureBeat通常使用 .article-content, .entry-content, article p
            content_selectors = [
                'article .article-content p',
                '.entry-content p',
                'article p',
                '[class*="article-body"] p',
                '[class*="post-content"] p'
            ]

            content_parts = []
            for selector in content_selectors:
                try:
                    paragraphs = await detail_page.query_selector_all(selector)
                    if paragraphs:
                        for para in paragraphs:
                            para_text = (await para.inner_text()).strip()
                            # 过滤掉非正文内容
                            if para_text and len(para_text) > 10:
                                # 排除导航、分享按钮等
                                if para_text not in ['Share', 'Subscribe', 'Follow', 'Related', '']:
                                    # 排除短作者信息行
                                    if len(para_text) > 30 or ',' not in para_text:
                                        content_parts.append(para_text)
                        if content_parts:
                            break
                except Exception:
                    continue

            full_content = '\n\n'.join(content_parts)
            return (full_content if full_content else None, author)

        except Exception as e:
            logger.error(f"【VentureBeat】获取文章详情失败 {article_url}: {e}")
            return (None, None)
        finally:
            if detail_page:
                await detail_page.close()

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取文章ID

        Args:
            url: 文章URL，如 https://venturebeat.com/ai/openai-launches-gpt-4-turbo/

        Returns:
            文章路径slug作为ID
        """
        try:
            # 提取最后一段路径作为ID
            match = re.search(r'/([^/]+)/?$', url)
            return match.group(1) if match else None
        except Exception:
            return None

    def _parse_datetime(self, date_text: str) -> datetime:
        """
        解析日期时间文本

        Args:
            date_text: 日期文本，如 "2025-11-13T10:30:00Z" 或 "November 13, 2025"

        Returns:
            datetime对象
        """
        try:
            # 尝试ISO格式
            if 'T' in date_text:
                # 去除时区信息
                date_text = date_text.replace('Z', '').split('+')[0].split('-')[0]
                return datetime.fromisoformat(date_text)

            # 尝试多种英文格式
            for fmt in ['%B %d, %Y', '%b %d, %Y', '%Y-%m-%d', '%d %B %Y']:
                try:
                    return datetime.strptime(date_text.strip(), fmt)
                except ValueError:
                    continue

            logger.warning(f"【VentureBeat】Failed to parse date text '{date_text}'")
            return datetime.now()
        except Exception as e:
            logger.error(f"【VentureBeat】Failed to parse date text '{date_text}': {e}")
            return datetime.now()

    async def _preprocess_items(self, items: List[Dict[str, Any]]) -> None:
        """
        预处理：在数据库会话外并发执行翻译和字段增强

        Args:
            items: 文章列表（会被原地修改）
        """
        if not items:
            return

        logger.info(f"【VentureBeat】开始预处理 {len(items)} 条消息（翻译 + 字段增强）")

        tasks = []
        for item in items:
            task = self._preprocess_single_item(item)
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _preprocess_single_item(self, item: Dict[str, Any]) -> None:
        """
        预处理单条消息（翻译 + 字段增强）

        Args:
            item: 文章数据（会被原地修改）
        """
        try:
            # 并发执行翻译和字段增强
            translation_task = self._generate_summary(item.get('excerpt', ''), item.get('content', ''))
            enrichment_task = self._enrich_fields(item.get('title', ''), item.get('content', ''))

            summary, enriched = await asyncio.gather(translation_task, enrichment_task)

            item['summary'] = summary
            item['region'] = enriched.get('region')
            item['industry_tags'] = enriched.get('industry_tags')

        except Exception as e:
            logger.error(f"【VentureBeat】预处理失败: {e}")
            item['summary'] = item.get('excerpt', '')[:500] if item.get('excerpt') else ''
            item['region'] = None
            item['industry_tags'] = None

    async def _enrich_fields(self, title: str, content: str) -> Dict[str, Optional[str]]:
        """
        字段增强（region + industry_tags）

        Args:
            title: 标题
            content: 内容

        Returns:
            包含region和industry_tags的字典
        """
        if not self.field_enricher:
            return {"region": None, "industry_tags": None}

        try:
            enriched = await self.field_enricher.enrich_fields(title, content)
            return enriched
        except Exception as e:
            logger.error(f"【VentureBeat】字段增强失败: {e}")
            return {"region": None, "industry_tags": None}

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
        存储到MySQL

        Args:
            items: 文章列表（已经过翻译和字段增强）
        """
        try:
            with create_session() as db:
                for item in items:
                    message = VentureBeatMessage(
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
                        category=item.get('category'),
                        language=item.get('language'),
                        excerpt=item.get('excerpt'),
                        featured_image=item.get('featured_image')
                    )

                    try:
                        db.add(message)
                        db.commit()
                        logger.debug(f"【VentureBeat】Inserted to MySQL: url={item.get('url')}")
                    except IntegrityError as e:
                        db.rollback()
                        if "Duplicate entry" in str(e):
                            logger.debug(f"【VentureBeat】Duplicate URL: {item['url']}")
                        else:
                            logger.error(f"【VentureBeat】MySQL insert error: {e}")
        except Exception as e:
            logger.error(f"【VentureBeat】Failed to store to MySQL: {e}")

    async def _store_to_chroma(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到ChromaDB

        Args:
            items: 文章列表
        """
        if not self.chroma_storage or not self.embedding_client:
            return

        try:
            for item in items:
                summary = item.get('summary', '')
                document_text = f"{item['title']} {summary}"

                embedding = self.embedding_client.generate_embedding(document_text)

                chroma_id = item.get('url') or str(uuid.uuid4())

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
                        "region": item.get('region', ''),
                        "industry_tags": item.get('industry_tags', ''),
                        "language": item.get('language', '')
                    }],
                    embeddings=[embedding]
                )
                logger.debug(f"【VentureBeat】Inserted to ChromaDB: url={item.get('url')}")
        except Exception as e:
            logger.error(f"【VentureBeat】Failed to store to ChromaDB: {e}")

    async def _generate_summary(self, excerpt: Optional[str], content: str) -> str:
        """
        生成摘要（支持中文翻译）

        外文内容自动翻译成中文

        Args:
            excerpt: 网页提取的摘要
            content: 正文内容

        Returns:
            摘要文本（中文）
        """
        # 1. 确定原始摘要来源
        source_text = excerpt if excerpt and len(excerpt.strip()) > 0 else content

        if not source_text:
            return ""

        # 2. 外文内容：翻译成中文
        if self.translator:
            try:
                # 全文翻译（不截断）
                translated = await self.translator.translate(
                    source_text,
                    context="VentureBeat科技新闻摘要"
                )
                return translated
            except Exception as e:
                logger.error(f"【VentureBeat】翻译失败: {e}")
                # 降级策略：返回截断原文
                return source_text[:500] + "... [AI翻译暂不可用]"
        else:
            # 无翻译器：返回截断原文
            if len(source_text) <= 1000:
                return source_text
            return source_text[:500] + "..."

    async def _close_browser(self) -> None:
        """关闭浏览器"""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.error(f"【VentureBeat】Failed to close browser: {e}")
