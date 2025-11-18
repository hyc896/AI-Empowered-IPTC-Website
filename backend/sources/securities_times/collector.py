# -*- coding: utf-8 -*-

"""
Securities Times Collector
证券时报采集器（中国财经新闻）

数据来源：
- 要闻栏目：https://www.stcn.com/article/list/yw.html

架构特点：
- 预处理模式：在数据库会话外完成字段增强
- 详情页抓取：列表页只有摘要，需访问详情页获取完整content
- 中文内容：无需翻译，但需要字段增强（region + industry_tags + ai_tag）
- 智能去重：通过URL去重，遇到已存在记录立即停止
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright
from sqlalchemy.exc import IntegrityError

from backend.database.entities import SecuritiesTimesMessage
from backend.database.connection import create_session

try:
    from backend.storage import get_chromadb_storage
    _chroma_available = True
except ImportError:
    _chroma_available = False

try:
    from backend.llm import get_embedding_client
    _llm_available = True
except ImportError:
    _llm_available = False

try:
    from backend.services import get_field_enricher
    _field_enricher_available = True
except ImportError:
    _field_enricher_available = False

logger = logging.getLogger(__name__)


class SecuritiesTimesCollector:
    """证券时报财经新闻采集器"""

    # 栏目配置
    CATEGORIES = {
        'yw': {
            'name': '要闻',
            'url': 'https://www.stcn.com/article/list/yw.html',
            'display': '要闻'
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
                - region: 地区（CN=China 中国）
                - language: 语言（zh）
        """
        # 从配置顶层读取基础字段
        self.source_id = config.get('id', 'auto')

        # 从嵌套的config字段读取详细配置
        self.config = config.get('config', {})
        self.interval = self.config.get('interval', 86400)
        self.mysql_table = self.config.get('mysql_table', 'mp_securities_times_messages')
        self.chroma_collection = self.config.get('chroma_collection', 'securities_times')
        self.region = self.config.get('region', 'CN')
        self.language = self.config.get('language', 'zh')

        # 要采集的栏目（默认全部）
        self.enabled_categories = self.config.get('categories', ['yw'])

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【证券时报】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
        else:
            self.embedding_client = None
            logger.warning("【证券时报】LLM服务不可用，将跳过向量化")

        if _field_enricher_available:
            self.field_enricher = get_field_enricher()
        else:
            self.field_enricher = None
            logger.warning("【证券时报】FieldEnricher不可用，将跳过字段增强")

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

            logger.info(f"【证券时报】采集器初始化成功（栏目: {', '.join(self.enabled_categories)}）")
            return True
        except Exception as e:
            logger.error(f"【证券时报】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【证券时报】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【证券时报】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【证券时报】采集失败: {e}")

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        await self._close_browser()
        logger.info("【证券时报】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集（流式处理架构）

        流程（Fail Fast原则）：
        1. 获取MySQL中最新文章URL
        2. 遍历所有启用的栏目
        3. 逐栏目采集 → 分批处理（每批10篇）
        4. 每批：访问详情页 → 字段增强 → 存储 → 下一批
        5. 单条失败不影响整体，立即记录错误
        """
        try:
            latest_url = await self._get_latest_stored_url()
            logger.debug(f"【证券时报】Latest stored URL: {latest_url}")

            total_processed = 0

            # 遍历所有栏目
            for category_key in self.enabled_categories:
                category_config = self.CATEGORIES.get(category_key)
                if not category_config:
                    logger.warning(f"【证券时报】未知栏目: {category_key}")
                    continue

                logger.info(f"【证券时报】开始采集栏目: {category_config['display']}")
                articles = await self._scrape_category(category_config, latest_url)

                if not articles:
                    logger.debug(f"【证券时报】栏目 {category_config['display']} 无新文章")
                    continue

                # 分批处理（每批10篇，防止并发过载）
                batch_size = 10
                for batch_start in range(0, len(articles), batch_size):
                    batch_end = min(batch_start + batch_size, len(articles))
                    batch = articles[batch_start:batch_end]

                    logger.info(
                        f"【证券时报】处理批次 [{batch_start+1}-{batch_end}/{len(articles)}] "
                        f"({category_config['display']})"
                    )

                    # 1. 访问详情页（串行，避免反爬虫）
                    for idx, item in enumerate(batch, batch_start + 1):
                        try:
                            full_content = await self._fetch_article_content(item['url'])
                            if full_content:
                                item['content'] = full_content
                                logger.debug(f"[{idx}/{len(articles)}] ✓ 详情: {item['url']}")
                            else:
                                # 降级：使用列表页的summary作为content
                                item['content'] = item.get('summary', item['title'])
                                logger.debug(f"[{idx}/{len(articles)}] ⚠ 使用摘要: {item['url']}")
                            # 延迟避免反爬虫
                            await asyncio.sleep(1)
                        except Exception as e:
                            logger.error(f"[{idx}/{len(articles)}] ✗ 详情页失败: {e}")
                            # Fail Fast：单条失败不影响批次，使用降级策略
                            item['content'] = item.get('summary', item['title'])

                    # 2. 预处理（字段增强，批内串行）
                    await self._preprocess_items(batch)

                    # 3. 存储（MySQL + ChromaDB）
                    await self._store_items(batch)

                    total_processed += len(batch)
                    logger.info(f"【证券时报】批次完成，已处理 {total_processed} 篇")

                    # 批次间延迟，降低服务器压力
                    if batch_end < len(articles):
                        await asyncio.sleep(2)

            if total_processed > 0:
                logger.info(f"【证券时报】采集完成，共处理 {total_processed} 篇新文章")
            else:
                logger.debug("【证券时报】没有发现新文章")

        except Exception as e:
            logger.error(f"【证券时报】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新文章的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(SecuritiesTimesMessage).filter(
                    SecuritiesTimesMessage.source_id == self.source_id,
                    SecuritiesTimesMessage.url.isnot(None)
                ).order_by(
                    SecuritiesTimesMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"【证券时报】Failed to get latest URL: {e}")
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
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                })

                await page.goto(category_config['url'], wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"【证券时报】第 {attempt + 1} 次尝试失败: {e}，{retry_delay}秒后重试...")
                    if page:
                        await page.close()
                        page = None
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【证券时报】所有重试均失败: {e}", exc_info=True)
                    if page:
                        await page.close()
                    return []

        if not page:
            return []

        try:
            # 证券时报使用article标签或列表项元素
            selectors_to_try = [
                'article',
                '.news-item',
                '.article-item',
                '[class*="news"]',
                'li[class*="item"]'
            ]

            selected_selector = None
            for selector in selectors_to_try:
                try:
                    await page.wait_for_selector(selector, timeout=10000)
                    test_elements = await page.query_selector_all(selector)
                    if test_elements:
                        selected_selector = selector
                        logger.debug(f"【证券时报】使用选择器: {selector}")
                        break
                except Exception:
                    continue

            if not selected_selector:
                logger.warning(f"【证券时报】未找到文章元素（栏目: {category_config['name']}）")
                return []

            # 滚动加载更多内容
            articles_list = []
            load_more_attempts = 0
            max_load_attempts = 20
            consecutive_no_new = 0
            max_consecutive_no_new = 3

            logger.info(f"【证券时报】开始滚动加载 {category_config['display']} 栏目...")

            while load_more_attempts < max_load_attempts:
                # 获取当前所有文章元素
                article_elements = await page.query_selector_all(selected_selector)
                current_count = len(article_elements)
                logger.debug(f"【证券时报】当前页面文章数: {current_count}")

                # 从上次结束的位置开始提取新文章
                start_index = len(articles_list)
                for idx in range(start_index, current_count):
                    article_elem = article_elements[idx]
                    article_data = await self._extract_article_from_element(article_elem, category_config['name'])

                    if not article_data:
                        continue

                    article_url = article_data.get('url')
                    if not article_url:
                        continue

                    # 遇到已存在URL立即停止
                    if latest_url and article_url == latest_url:
                        logger.info(f"【证券时报】遇到已存储URL，停止采集（共 {len(articles_list)} 篇新文章）")
                        return articles_list

                    articles_list.append(article_data)

                # 检查是否有新文章
                if len(articles_list) == start_index:
                    consecutive_no_new += 1
                    logger.debug(f"【证券时报】本次滚动未发现新内容 ({consecutive_no_new}/{max_consecutive_no_new})")
                    if consecutive_no_new >= max_consecutive_no_new:
                        logger.info(f"【证券时报】连续{max_consecutive_no_new}次无新内容，停止滚动（共 {len(articles_list)} 篇）")
                        break
                else:
                    consecutive_no_new = 0
                    logger.debug(f"【证券时报】新增 {len(articles_list) - start_index} 篇文章")

                # 滚动到页面底部触发加载
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(3)

                load_more_attempts += 1

            logger.info(f"【证券时报】{category_config['display']} 栏目共提取 {len(articles_list)} 篇文章")
            return articles_list

        except Exception as e:
            logger.error(f"【证券时报】Failed to scrape category {category_config['name']}: {e}", exc_info=True)
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
            title_elem = await article_elem.query_selector('a[href*="/article/detail/"]')
            if not title_elem:
                # 尝试其他选择器
                title_elem = await article_elem.query_selector('h2 a, h3 a, .title a, a')

            if not title_elem:
                return None

            url = await title_elem.get_attribute('href')
            title_text = await title_elem.inner_text()
            title = title_text.strip() if title_text else None

            if not url or not title:
                return None

            # 确保URL是完整的
            if not url.startswith('http'):
                url = f"https://www.stcn.com{url}"

            # 提取文章ID
            external_id = self._extract_id_from_url(url)

            # 提取摘要
            summary_elem = await article_elem.query_selector('.summary, .excerpt, .desc, [class*="desc"]')
            summary = ""
            if summary_elem:
                summary_text = await summary_elem.inner_text()
                summary = summary_text.strip() if summary_text else ""

            # 提取发布时间
            time_elem = await article_elem.query_selector('time, .time, .date, [class*="time"]')
            published_at = datetime.now()
            if time_elem:
                time_text = await time_elem.inner_text()
                if time_text:
                    published_at = self._parse_datetime(time_text.strip())

            # 提取作者（byline格式：来源：证券时报网作者：xxx）
            byline_elem = await article_elem.query_selector('.author, .byline, [class*="author"]')
            provider = None
            if byline_elem:
                byline_text = await byline_elem.inner_text()
                provider = self._extract_authors(byline_text)

            # 提取标签
            tag_elems = await article_elem.query_selector_all('.tag, .label, [class*="tag"]')
            tags = []
            for tag_elem in tag_elems:
                tag_text = await tag_elem.inner_text()
                if tag_text:
                    tags.append(tag_text.strip())

            return {
                "external_id": external_id,
                "title": title,
                "summary": summary if summary else title,  # 摘要优先，无则用标题
                "provider": provider,
                "published_at": published_at,
                "url": url,
                "category": category,
                "language": self.language,
                "tags": tags if tags else None,
                "region": None,  # 将由field_enricher填充
                "industry_tags": None,  # 将由field_enricher填充
                "ai_tag": None  # 将由field_enricher填充
            }
        except Exception as e:
            logger.error(f"【证券时报】Failed to extract article: {e}")
            return None

    async def _fetch_article_content(self, article_url: str) -> Optional[str]:
        """
        访问文章详情页，获取完整内容

        Args:
            article_url: 文章URL

        Returns:
            完整的文章内容
        """
        detail_page: Optional[Page] = None
        max_retries = 3
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                detail_page = await self._browser.new_page()

                await detail_page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                })

                await detail_page.goto(article_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(2)
                break

            except Exception as e:
                if detail_page:
                    await detail_page.close()
                    detail_page = None

                if attempt < max_retries - 1:
                    logger.warning(f"【证券时报】详情页第 {attempt + 1} 次尝试失败 {article_url}: {e}，{retry_delay}秒后重试...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【证券时报】详情页所有重试均失败 {article_url}: {e}")
                    return None

        if not detail_page:
            return None

        try:
            # 提取文章正文内容
            # 证券时报使用 .detail-content, .article-content, article p
            content_selectors = [
                '.detail-content p',
                '.article-content p',
                'article .content p',
                '[class*="article-body"] p',
                'article p'
            ]

            content_parts = []
            for selector in content_selectors:
                try:
                    paragraphs = await detail_page.query_selector_all(selector)
                    if paragraphs:
                        for para in paragraphs:
                            para_text = await para.inner_text()
                            if para_text:
                                para_text = para_text.strip()

                            # 过滤掉非正文内容
                            if not para_text or len(para_text) <= 10:
                                continue

                            # 排除常见的非正文元素
                            skip_patterns = [
                                '分享', '订阅', '关注', '相关', '来源：', '作者：',
                                '责任编辑', '版权声明', '免责声明'
                            ]
                            if any(pattern in para_text for pattern in skip_patterns):
                                continue

                            content_parts.append(para_text)
                        if content_parts:
                            break
                except Exception:
                    continue

            full_content = '\n\n'.join(content_parts)
            return full_content if full_content else None

        except Exception as e:
            logger.error(f"【证券时报】获取文章详情失败 {article_url}: {e}")
            return None
        finally:
            if detail_page:
                await detail_page.close()

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取文章ID

        Args:
            url: 文章URL，如 https://www.stcn.com/article/detail/3500937.html

        Returns:
            文章ID（如3500937）
        """
        try:
            # 提取/detail/后面的数字
            match = re.search(r'/detail/(\d+)\.html', url)
            return match.group(1) if match else None
        except Exception:
            return None

    def _extract_authors(self, byline: str) -> Optional[str]:
        """
        从byline中提取作者

        Args:
            byline: byline文本，如"来源：证券时报网作者：卓泳 安宇飞"

        Returns:
            作者名，多个用逗号分隔
        """
        try:
            if not byline:
                return None

            # 提取"作者："后面的内容
            if '作者：' in byline:
                authors_text = byline.split('作者：')[1].strip()
                # 去除多余的空格，用逗号分隔
                authors = ' '.join(authors_text.split())
                return authors
            elif '来源：' in byline:
                source_text = byline.split('来源：')[1].strip()
                # 如果还有"作者："则继续分割
                if '作者：' in source_text:
                    return source_text.split('作者：')[1].strip()
                return source_text.split()[0] if source_text else None
            return None
        except Exception:
            return None

    def _parse_datetime(self, date_text: str) -> datetime:
        """
        解析日期时间文本

        Args:
            date_text: 日期文本，如 "2025-11-18 21:58" 或 "21:58"

        Returns:
            datetime对象
        """
        try:
            # 完整日期时间格式
            if '-' in date_text:
                try:
                    return datetime.strptime(date_text.strip(), '%Y-%m-%d %H:%M')
                except ValueError:
                    pass

            # 仅时间格式（如"21:58"），使用今天的日期
            if ':' in date_text and '-' not in date_text:
                try:
                    time_parts = date_text.strip().split(':')
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    today = datetime.now()
                    return today.replace(hour=hour, minute=minute, second=0, microsecond=0)
                except (ValueError, IndexError):
                    pass

            logger.warning(f"【证券时报】Failed to parse date text '{date_text}'")
            return datetime.now()
        except Exception as e:
            logger.error(f"【证券时报】Failed to parse date text '{date_text}': {e}")
            return datetime.now()

    async def _preprocess_items(self, items: List[Dict[str, Any]]) -> None:
        """
        预处理：在数据库会话外并发执行字段增强

        Args:
            items: 文章列表（会被原地修改）

        架构改进：
        - 批内串行处理（不使用asyncio.gather），避免并发过载
        - FieldEnricher内部已有并发控制
        - 单条失败不影响其他，立即记录错误
        """
        if not items:
            return

        logger.info(f"【证券时报】开始预处理 {len(items)} 条消息（字段增强）")

        # 串行处理每条消息
        for idx, item in enumerate(items, 1):
            # 提前生成message_id用于事件发布
            message_id = str(uuid.uuid4())
            item['message_id'] = message_id

            try:
                await self._preprocess_single_item(item, message_id)
                logger.debug(f"【证券时报】预处理完成 [{idx}/{len(items)}]: {item.get('title', '')[:30]}")
            except Exception as e:
                logger.error(f"【证券时报】预处理失败 [{idx}/{len(items)}]: {e}")
                # Fail Fast：失败时设置降级值，继续处理
                item['region'] = None
                item['industry_tags'] = None
                item['ai_tag'] = None

    async def _preprocess_single_item(self, item: Dict[str, Any], message_id: str) -> None:
        """
        预处理单条消息（字段增强）

        Args:
            item: 文章数据（会被原地修改）
            message_id: 消息ID（用于事件发布）
        """
        # 字段增强（try-catch，失败设为None）
        try:
            enriched = await self._enrich_fields(
                item.get('title', ''),
                item.get('content', ''),
                message_id
            )
            item['region'] = enriched.get('region')
            item['industry_tags'] = enriched.get('industry_tags')
            item['ai_tag'] = enriched.get('ai_tag')
        except Exception as e:
            logger.error(f"【证券时报】字段增强失败 (url={item.get('url')}): {e}")
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
                source_name="证券时报"
            )
            return enriched
        except Exception as e:
            logger.error(f"【证券时报】字段增强失败: {e}")
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
        存储到MySQL

        Args:
            items: 文章列表（已经过字段增强）
        """
        try:
            with create_session() as db:
                for item in items:
                    message = SecuritiesTimesMessage(
                        id=item.get('message_id', str(uuid.uuid4())),
                        source_id=self.source_id,
                        external_id=item.get('external_id'),
                        title=item['title'],
                        content=item.get('content', item.get('summary', '')),
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
                        tags=item.get('tags')
                    )

                    try:
                        db.add(message)
                        db.commit()
                        logger.debug(f"【证券时报】Inserted to MySQL: url={item.get('url')}")
                    except IntegrityError as e:
                        db.rollback()
                        if "Duplicate entry" in str(e):
                            logger.debug(f"【证券时报】Duplicate URL: {item['url']}")
                        else:
                            logger.error(f"【证券时报】MySQL insert error: {e}")
        except Exception as e:
            logger.error(f"【证券时报】Failed to store to MySQL: {e}")

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
                        "ai_tag": item.get('ai_tag', ''),
                        "language": item.get('language', '')
                    }],
                    embeddings=[embedding]
                )
                logger.debug(f"【证券时报】Inserted to ChromaDB: url={item.get('url')}")
        except Exception as e:
            logger.error(f"【证券时报】Failed to store to ChromaDB: {e}")

    async def _close_browser(self) -> None:
        """关闭浏览器"""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.error(f"【证券时报】Failed to close browser: {e}")
