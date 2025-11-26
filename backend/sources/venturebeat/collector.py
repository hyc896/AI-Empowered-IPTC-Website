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
from playwright.async_api import Browser, Page
from sqlalchemy.exc import IntegrityError

from backend.database.entities import VentureBeatMessage
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


class VentureBeatCollector(PlaywrightCollectorBase):
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
        super().__init__(config)

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

            logger.info(f"【VentureBeat】采集器初始化成功（栏目: {', '.join(self.enabled_categories)}）")
            return True
        except Exception as e:
            logger.error(f"【VentureBeat】采集器初始化失败: {e}")
            return False





    async def _collect_once(self) -> None:
        """
        单次采集（流式处理架构）

        流程（Fail Fast原则）：
        1. 获取MySQL中已存在的URL集合（用于去重）
        2. 遍历所有启用的栏目
        3. 逐栏目采集 → 分批处理（每批10篇）
        4. 每批：访问详情页 → 翻译 → 存储 → 下一批
        5. 单条失败不影响整体，立即记录错误

        关键改进：
        - 边采集边处理，不等待全部完成
        - 分批控制并发翻译，防止API过载
        - 单条失败立即暴露，不阻塞后续处理
        - 使用URL集合去重，支持多栏目独立检测
        """
        try:
            existing_urls = await self._get_existing_urls()
            logger.info(f"【VentureBeat】已存在 {len(existing_urls)} 条URL用于去重")

            total_processed = 0

            # 遍历所有栏目
            for category_key in self.enabled_categories:
                category_config = self.CATEGORIES.get(category_key)
                if not category_config:
                    logger.warning(f"【VentureBeat】未知栏目: {category_key}")
                    continue

                logger.info(f"【VentureBeat】开始采集栏目: {category_config['display']}")
                articles = await self._scrape_category(category_config, existing_urls)

                if not articles:
                    logger.debug(f"【VentureBeat】栏目 {category_config['display']} 无新文章")
                    continue

                # 分批处理（每批10篇，防止并发过载）
                batch_size = 10
                for batch_start in range(0, len(articles), batch_size):
                    batch_end = min(batch_start + batch_size, len(articles))
                    batch = articles[batch_start:batch_end]

                    logger.info(
                        f"【VentureBeat】处理批次 [{batch_start+1}-{batch_end}/{len(articles)}] "
                        f"({category_config['display']})"
                    )

                    # 1. 访问详情页（串行，避免反爬虫）
                    for idx, item in enumerate(batch, batch_start + 1):
                        try:
                            referer_url = item.get('category_url')
                            full_content, author = await self._fetch_article_content(item['url'], referer_url)
                            if full_content:
                                item['content'] = full_content
                                if author and not item.get('provider'):
                                    item['provider'] = author
                                logger.debug(f"[{idx}/{len(articles)}] ✓ 详情: {item['url']}")
                            else:
                                logger.debug(f"[{idx}/{len(articles)}] ⚠ 使用摘要: {item['url']}")
                            # 延迟避免反爬虫
                            await asyncio.sleep(1)
                        except Exception as e:
                            logger.error(f"[{idx}/{len(articles)}] ✗ 详情页失败: {e}")
                            # Fail Fast：单条失败不影响批次，继续处理

                    # 2. 预处理（翻译+字段增强，批内并发）
                    await self._preprocess_items(batch)

                    # 3. 存储（MySQL + ChromaDB）
                    await self._store_items(batch)

                    total_processed += len(batch)
                    logger.info(f"【VentureBeat】批次完成，已处理 {total_processed} 篇")

                    # 批次间延迟，降低API压力
                    if batch_end < len(articles):
                        await asyncio.sleep(2)

            if total_processed > 0:
                logger.info(f"【VentureBeat】采集完成，共处理 {total_processed} 篇新文章")
            else:
                logger.debug("【VentureBeat】没有发现新文章")

        except Exception as e:
            logger.error(f"【VentureBeat】采集错误: {e}", exc_info=True)

    async def _get_existing_urls(self, limit: int = 1000) -> set:
        """
        获取MySQL中已存在的URL集合（用于去重）

        Args:
            limit: 最多获取的URL数量（默认1000，覆盖近期数据）

        Returns:
            已存在URL的集合
        """
        try:
            with create_session() as db:
                results = db.query(VentureBeatMessage.url).filter(
                    VentureBeatMessage.source_id == self.source_id,
                    VentureBeatMessage.url.isnot(None)
                ).order_by(
                    VentureBeatMessage.crawled_at.desc()
                ).limit(limit).all()

                return {str(row[0]) for row in results if row[0]}
        except Exception as e:
            logger.error(f"【VentureBeat】Failed to get existing URLs: {e}")
            return set()

    async def _scrape_category(
        self,
        category_config: Dict[str, str],
        existing_urls: set
    ) -> List[Dict[str, Any]]:
        """
        爬取单个栏目的文章列表

        Args:
            category_config: 栏目配置
            existing_urls: 已存在的URL集合，用于去重

        Returns:
            文章列表（仅包含新文章）
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

            selected_selector = None
            for selector in selectors_to_try:
                try:
                    await page.wait_for_selector(selector, timeout=10000)
                    test_elements = await page.query_selector_all(selector)
                    if test_elements:
                        selected_selector = selector
                        logger.debug(f"【VentureBeat】使用选择器: {selector}")
                        break
                except Exception:
                    continue

            if not selected_selector:
                logger.warning(f"【VentureBeat】未找到文章元素（栏目: {category_config['name']}）")
                return []

            # 滚动加载更多内容
            articles_list = []
            load_more_attempts = 0
            max_load_attempts = 20  # 最多滚动20次
            consecutive_all_duplicate = 0  # 连续全部重复计数
            max_consecutive_all_duplicate = 2  # 连续2次全部重复则停止（说明已到达旧内容区域）
            consecutive_no_new = 0
            max_consecutive_no_new = 3  # 连续3次无新内容则停止

            logger.info(f"【VentureBeat】开始滚动加载 {category_config['display']} 栏目...")

            processed_element_count = 0  # 已处理的元素数量

            while load_more_attempts < max_load_attempts:
                # 获取当前所有文章元素
                article_elements = await page.query_selector_all(selected_selector)
                current_count = len(article_elements)
                logger.debug(f"【VentureBeat】当前页面文章数: {current_count}")

                # 从上次结束的位置开始提取新文章
                new_in_this_scroll = 0
                duplicate_in_this_scroll = 0

                for idx in range(processed_element_count, current_count):
                    article_elem = article_elements[idx]
                    article_data = await self._extract_article_from_element(article_elem, category_config['name'])

                    if not article_data:
                        continue

                    article_url = article_data.get('url')
                    if not article_url:
                        continue

                    # 检查URL是否已存在
                    if article_url in existing_urls:
                        duplicate_in_this_scroll += 1
                        logger.debug(f"【VentureBeat】跳过已存在URL: {article_url[:60]}...")
                        continue

                    # 新文章：添加到列表
                    article_data['category_url'] = category_config['url']
                    articles_list.append(article_data)
                    new_in_this_scroll += 1

                processed_element_count = current_count

                # 智能停止逻辑
                if new_in_this_scroll == 0 and duplicate_in_this_scroll > 0:
                    # 本次滚动全部是重复的
                    consecutive_all_duplicate += 1
                    consecutive_no_new = 0
                    logger.debug(
                        f"【VentureBeat】本次滚动全部重复 "
                        f"({consecutive_all_duplicate}/{max_consecutive_all_duplicate})"
                    )
                    if consecutive_all_duplicate >= max_consecutive_all_duplicate:
                        logger.info(
                            f"【VentureBeat】连续{max_consecutive_all_duplicate}次全部重复，"
                            f"停止滚动（共 {len(articles_list)} 篇新文章）"
                        )
                        break
                elif new_in_this_scroll == 0 and duplicate_in_this_scroll == 0:
                    # 本次滚动没有任何内容（页面可能没有更多了）
                    consecutive_no_new += 1
                    consecutive_all_duplicate = 0
                    logger.debug(f"【VentureBeat】本次滚动无内容 ({consecutive_no_new}/{max_consecutive_no_new})")
                    if consecutive_no_new >= max_consecutive_no_new:
                        logger.info(
                            f"【VentureBeat】连续{max_consecutive_no_new}次无新内容，"
                            f"停止滚动（共 {len(articles_list)} 篇）"
                        )
                        break
                else:
                    # 有新文章，重置计数器
                    consecutive_all_duplicate = 0
                    consecutive_no_new = 0
                    logger.debug(f"【VentureBeat】新增 {new_in_this_scroll} 篇，跳过 {duplicate_in_this_scroll} 篇重复")

                # 滚动到页面底部触发加载
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(3)

                load_more_attempts += 1

            logger.info(f"【VentureBeat】{category_config['display']} 栏目共提取 {len(articles_list)} 篇新文章")
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

            # 提取摘要/excerpt（移除通用p选择器，避免误选图片说明）
            excerpt_elem = await article_elem.query_selector('.excerpt, [class*="excerpt"], [class*="summary"], [class*="description"]')
            excerpt = ""
            if excerpt_elem:
                excerpt_text = (await excerpt_elem.inner_text()).strip()

                # 过滤无效内容（PARTNER CONTENT、图片说明等）
                invalid_excerpts = [
                    'partner content',
                    'sponsored content',
                    'image credit:',
                    'credit: venturebeat',
                    'illustration of',
                    'image source:',
                    'ai illustration'
                ]

                # 检查是否为无效excerpt
                excerpt_lower = excerpt_text.lower()
                is_invalid = any(pattern in excerpt_lower for pattern in invalid_excerpts)

                # 检查是否过短（少于20字符通常不是真正的摘要）
                if not is_invalid and len(excerpt_text) >= 20:
                    excerpt = excerpt_text
                else:
                    logger.debug(f"【VentureBeat】过滤无效excerpt: {excerpt_text[:50]}...")

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

    async def _fetch_article_content(
        self,
        article_url: str,
        referer_url: Optional[str] = None
    ) -> tuple[Optional[str], Optional[str]]:
        """
        访问文章详情页，获取完整内容和作者

        Args:
            article_url: 文章URL
            referer_url: 来源页面URL（列表页URL）

        Returns:
            (完整的文章内容, 作者名)
        """
        detail_page: Optional[Page] = None
        max_retries = 3
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                detail_page = await self._browser.new_page()

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
                if referer_url:
                    headers['Referer'] = referer_url

                await detail_page.set_extra_http_headers(headers)

                await detail_page.goto(article_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(2)
                break

            except Exception as e:
                if detail_page:
                    await detail_page.close()
                    detail_page = None

                if attempt < max_retries - 1:
                    logger.warning(f"【VentureBeat】详情页第 {attempt + 1} 次尝试失败 {article_url}: {e}，{retry_delay}秒后重试...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【VentureBeat】详情页所有重试均失败 {article_url}: {e}")
                    return (None, None)

        if not detail_page:
            return (None, None)

        try:

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
                            if not para_text or len(para_text) <= 10:
                                continue

                            # 排除导航、分享按钮等
                            if para_text in ['Share', 'Subscribe', 'Follow', 'Related', '']:
                                continue

                            # 排除图片来源和描述
                            image_credit_patterns = [
                                'image credit:',
                                '图片来源：',
                                'image source:',
                                'photo credit:',
                                'illustration credit:',
                                'generated by',
                                'generated using',
                                'using midjourney',
                                'using dalle',
                                'using chatgpt',
                                'using flux',
                                'partner content',
                                '合作伙伴内容',
                                'sponsored content'
                            ]
                            if any(pattern in para_text.lower() for pattern in image_credit_patterns):
                                continue

                            # 排除短作者信息行
                            if len(para_text) < 30 and ',' in para_text:
                                continue

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
                # 去除时区信息（Z或+XX:XX或-XX:XX）
                date_text = date_text.replace('Z', '')
                # 使用正则表达式移除时区偏移（如+08:00或-05:00）
                date_text = re.sub(r'[+-]\d{2}:\d{2}$', '', date_text)
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

        架构改进：
        - 批内串行处理（不使用asyncio.gather），避免并发过载
        - Translator内部的semaphore(2)已经控制并发
        - 单条失败不影响其他，立即记录错误
        """
        if not items:
            return

        logger.info(f"【VentureBeat】开始预处理 {len(items)} 条消息（翻译 + 字段增强）")

        # 串行处理每条消息（Translator内部有并发控制）
        for idx, item in enumerate(items, 1):
            # 提前生成message_id用于事件发布
            message_id = str(uuid.uuid4())
            item['message_id'] = message_id

            try:
                await self._preprocess_single_item(item, message_id)
                logger.debug(f"【VentureBeat】预处理完成 [{idx}/{len(items)}]: {item.get('title', '')[:30]}")
            except Exception as e:
                logger.error(f"【VentureBeat】预处理失败 [{idx}/{len(items)}]: {e}")
                # Fail Fast：失败时设置降级值，继续处理
                item['summary'] = item.get('excerpt', '')[:500] if item.get('excerpt') else ''
                item['region'] = None
                item['industry_tags'] = None

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
        # 清理content中可能残留的图片描述（双重保险）
        cleaned_content = self._clean_image_credits(item.get('content', ''))

        # 1. 翻译（单独try-catch，失败使用降级）
        try:
            summary = await self._generate_summary(item.get('excerpt', ''), cleaned_content)
            item['summary'] = summary
        except Exception as e:
            logger.error(f"【VentureBeat】翻译失败 (url={item.get('url')}): {e}")
            item['summary'] = item.get('excerpt', '')[:500] if item.get('excerpt') else ''

        # 2. 字段增强（单独try-catch，失败设为None）
        try:
            enriched = await self._enrich_fields(item.get('title', ''), cleaned_content, message_id)
            item['region'] = enriched.get('region')
            item['industry_tags'] = enriched.get('industry_tags')
            item['ai_tag'] = enriched.get('ai_tag')
        except Exception as e:
            logger.error(f"【VentureBeat】字段增强失败 (url={item.get('url')}): {e}")
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
                message_id=message_id
            )
            return enriched
        except Exception as e:
            logger.error(f"【VentureBeat】字段增强失败: {e}")
            return {"region": None, "industry_tags": None, "ai_tag": None}

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        """
        串行存储到MySQL和ChromaDB

        注意：在Celery solo pool + nest_asyncio环境下，asyncio.gather会导致任务上下文冲突
        改为串行执行以保证稳定性

        Args:
            items: 文章列表
        """
        await self._store_to_mysql(items)
        await self._store_to_chroma(items)

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
                        id=item.get('message_id', str(uuid.uuid4())),
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
                        "region": item.get('region', ''),
                        "industry_tags": item.get('industry_tags', ''),
                        "language": item.get('language', '')
                    }],
                    embeddings=[embedding]
                )
                logger.debug(f"【VentureBeat】Inserted to ChromaDB: url={item.get('url')}")
        except Exception as e:
            logger.error(f"【VentureBeat】Failed to store to ChromaDB: {e}")

    def _clean_image_credits(self, text: str) -> str:
        """
        清理图片来源和描述文本

        Args:
            text: 原始文本

        Returns:
            清理后的文本
        """
        if not text:
            return ""

        lines = text.split('\n')
        cleaned_lines = []

        image_credit_patterns = [
            'image credit:',
            '图片来源：',
            'image source:',
            'photo credit:',
            'illustration credit:',
            'generated by',
            'generated using',
            'using midjourney',
            'using dalle',
            'using chatgpt',
            'using flux',
            'partner content',
            '合作伙伴内容',
            'sponsored content'
        ]

        for line in lines:
            line_lower = line.strip().lower()
            # 跳过包含图片描述的行
            if any(pattern in line_lower for pattern in image_credit_patterns):
                continue
            # 跳过空行
            if not line.strip():
                continue
            cleaned_lines.append(line.strip())

        return '\n'.join(cleaned_lines)

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

        # 2. 清理图片来源等无关文本
        source_text = self._clean_image_credits(source_text)

        if not source_text:
            return ""

        # 3. 外文内容：翻译成中文
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


