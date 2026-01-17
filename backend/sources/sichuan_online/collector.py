# -*- coding: utf-8 -*-

"""
四川在线采集器
SichuanOnline Collector

数据来源：http://dzrb.dzng.com/
特点：四川省地方新闻门户，包含基层治理典型
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import Browser, Page
from sqlalchemy.exc import IntegrityError

from backend.database.entities import SichuanOnlineMessage
from backend.database.connection import create_session
from backend.collectors.base import PlaywrightCollectorBase

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


class SichuanOnlineCollector(PlaywrightCollectorBase):
    """四川在线采集器（山东地方新闻与县域基层实践）"""

    def __init__(self, config: Dict[str, Any]):
        """初始化采集器"""
        super().__init__(config)

        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.source_id = config.get('id', 'auto')

        self.url = config['config'].get('url', 'https://sichuan.scol.com.cn/')
        self.region = config['config'].get('region', '中国')
        self.language = config['config'].get('language', 'zh')
        self.max_articles = config['config'].get('max_articles', 20)

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【四川在线】ChromaDB不可用")

        if _llm_available:
            self.embedding_client = get_embedding_client()
        else:
            self.embedding_client = None
            logger.warning("【四川在线】Embedding服务不可用")

        if _field_enricher_available:
            self.field_enricher = get_field_enricher()
        else:
            self.field_enricher = None
            logger.warning("【四川在线】FieldEnricher不可用")

    async def _on_initialize(self) -> bool:
        """初始化ChromaDB collection"""
        try:
            if self.chroma_storage:
                self.chroma_storage.create_collection(
                    collection_name=self.chroma_collection
                )
            logger.info(f"【四川在线】采集器初始化成功")
            return True
        except Exception as e:
            logger.error(f"【四川在线】初始化失败: {e}")
            return False

    async def _collect_once(self) -> None:
        """单次采集（三阶段架构）"""
        try:
            existing_urls = await self._get_existing_urls()
            logger.info(f"【四川在线】已存在 {len(existing_urls)} 条URL")

            articles = await self._scrape_articles(existing_urls)
            if not articles:
                logger.info("【四川在线】无新文章")
                return

            logger.info(f"【四川在线】采集到 {len(articles)} 篇新文章")

            # 阶段2：字段补全
            enriched_articles = await self._enrich_fields(articles)

            # 阶段3：存储
            await self._store_articles(enriched_articles)

            logger.info(f"【四川在线】本轮采集完成，新增 {len(enriched_articles)} 篇")

        except Exception as e:
            logger.error(f"【四川在线】采集失败: {e}", exc_info=True)
            raise

    async def _get_existing_urls(self) -> set:
        """获取数据库中已存在的URL"""
        try:
            with create_session() as db:
                results = db.query(SichuanOnlineMessage.url).all()
                return {row[0] for row in results}
        except Exception as e:
            logger.error(f"【四川在线】获取已存在URL失败: {e}")
            return set()

    async def _scrape_articles(self, existing_urls: set) -> List[Dict[str, Any]]:
        """阶段1：网页抓取"""
        articles = []
        page = None

        try:
            page = await self._browser.new_page()

            logger.info(f"【四川在线】访问: {self.url}")
            await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)

            # 尝试多种选择器提取新闻链接
            selectors_to_try = [
                'h3 a',
                'h2 a',
                'h4 a',
                '.list-item a',
                '.news-list a',
                'ul li a',
                '.title a',
                'article a'
            ]

            links = []
            for selector in selectors_to_try:
                links = await page.query_selector_all(selector)
                if len(links) > 5:
                    logger.info(f"【四川在线】使用选择器: {selector}, 找到 {len(links)} 个链接")
                    break

            processed = 0
            for link in links:
                if processed >= self.max_articles:
                    break

                try:
                    href = await link.get_attribute('href')
                    title_text = await link.inner_text()

                    if not href or not title_text:
                        continue

                    # 限制title长度，只取前200字符
                    title = title_text.strip()[:200]

                    if len(title) < 5:
                        continue

                    # 处理相对链接
                    if href.startswith('/'):
                        href = f"https://sichuan.scol.com.cn{href}"
                    elif not href.startswith('http'):
                        href = f"https://sichuan.scol.com.cn/{href}"

                    # 跳过频道首页链接（只保留实际新闻文章）
                    # 频道链接特征：以城市名或栏目名结尾，没有具体文章ID
                    if href.endswith('.scol.com.cn/') or href.endswith('.scol.com.cn') or \
                       '/ggxw/' in href or '/gcdt/' in href or '/dwgk/' in href or \
                       '/tfrm/' in href or '/spsc/' in href or '/amsc/' in href:
                        continue

                    # 只采集包含文章ID的URL（通常包含数字或特定路径）
                    if not any(char.isdigit() for char in href.split('/')[-1]):
                        continue

                    # 跳过已存在的URL
                    if href in existing_urls:
                        continue

                    articles.append({
                        'url': href,
                        'title': title.strip(),
                        'provider': '四川在线',
                    })
                    processed += 1

                except Exception as e:
                    logger.warning(f"【四川在线】提取链接失败: {e}")
                    continue

        except Exception as e:
            logger.error(f"【四川在线】抓取失败: {e}", exc_info=True)
        finally:
            if page:
                await page.close()

        return articles

    async def _enrich_fields(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """阶段2：字段补全（使用LLM或爬取详情页）"""
        enriched = []

        for i, article in enumerate(articles, 1):
            page = None
            try:
                logger.info(f"【四川在线】补全字段 ({i}/{len(articles)}): {article['title'][:30]}")

                # 访问详情页提取内容
                page = await self._browser.new_page()
                await page.goto(article['url'], wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(2)

                # 提取正文内容
                content = await self._extract_content(page)

                # 提取发布时间
                published_at = await self._extract_publish_time(page)

                article['content'] = content
                article['published_at'] = published_at

                # 生成摘要
                if content:
                    article['summary'] = content[:200]
                else:
                    article['summary'] = ""

                enriched.append(article)

            except Exception as e:
                logger.error(f"【四川在线】字段补全失败 {article['url']}: {e}")
                continue
            finally:
                if page:
                    await page.close()

        return enriched

    async def _extract_content(self, page: Page) -> str:
        """从详情页提取正文内容"""
        try:
            # 尝试多种选择器
            selectors = [
                '.article-content',
                '.content',
                '.text',
                '#content',
                'article',
                '.article',
                '[class*="content"]',
                '[class*="article"]'
            ]

            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        content = await element.inner_text()
                        if content and len(content) > 100:
                            return content.strip()
                except Exception:
                    continue

            # 如果找不到内容，记录警告
            logger.warning(f"【四川在线】无法获取内容: {page.url}")
            return ""

        except Exception as e:
            logger.error(f"【四川在线】提取内容失败: {e}")
            return ""

    async def _extract_publish_time(self, page: Page) -> Optional[datetime]:
        """从详情页提取发布时间"""
        try:
            # 尝试多种选择器和格式
            selectors = [
                '.time',
                '.date',
                '.publish-time',
                '[class*="time"]',
                '[class*="date"]'
            ]

            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        time_text = await element.inner_text()

                        # 尝试解析时间
                        patterns = [
                            r'(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})',
                            r'(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})',
                            r'(\d{4})-(\d{2})-(\d{2})',
                            r'(\d{4})年(\d{1,2})月(\d{1,2})日\s+(\d{2}):(\d{2})',
                            r'(\d{4})年(\d{1,2})月(\d{1,2})日'
                        ]

                        for pattern in patterns:
                            match = re.search(pattern, time_text)
                            if match:
                                groups = match.groups()
                                if len(groups) >= 6:
                                    return datetime(int(groups[0]), int(groups[1]), int(groups[2]),
                                                  int(groups[3]), int(groups[4]), int(groups[5]))
                                elif len(groups) >= 5:
                                    return datetime(int(groups[0]), int(groups[1]), int(groups[2]),
                                                  int(groups[3]), int(groups[4]))
                                elif len(groups) >= 3:
                                    return datetime(int(groups[0]), int(groups[1]), int(groups[2]))

                except Exception:
                    continue

            return None

        except Exception as e:
            logger.error(f"【四川在线】提取时间失败: {e}")
            return None

    async def _store_articles(self, articles: List[Dict[str, Any]]) -> None:
        """阶段3：存储到数据库和向量库"""
        with create_session() as db:
            for article in articles:
                try:
                    message = SichuanOnlineMessage(
                        id=str(uuid.uuid4()),
                        source_id=self.source_id,
                        external_id=self._extract_external_id(article['url']),
                        title=article['title'],
                        content=article['content'],
                        summary=article.get('summary', ''),
                        provider=article['provider'],
                        published_at=article.get('published_at'),
                        url=article['url'],
                        region=self.region,
                        language=self.language,
                        crawled_at=datetime.now()
                    )

                    db.add(message)
                    db.commit()
                    logger.info(f"【四川在线】已保存: {article['title'][:30]}")

                except IntegrityError:
                    db.rollback()
                    logger.warning(f"【四川在线】重复URL: {article['url']}")
                except Exception as e:
                    db.rollback()
                    logger.error(f"【四川在线】保存失败: {e}")

    def _extract_external_id(self, url: str) -> str:
        """从URL中提取外部ID"""
        try:
            match = re.search(r'/(\d+)\.html', url)
            if match:
                return match.group(1)
            return url.split('/')[-1].split('.')[0]
        except:
            return url[-50:]
