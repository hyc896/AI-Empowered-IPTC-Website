# -*- coding: utf-8 -*-

"""
红网采集器
Rednet Collector

数据来源：https://hn.rednet.cn/
特点：湖南地方新闻门户，内容涵盖时政、民生、经济等
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import Browser, Page
from sqlalchemy.exc import IntegrityError

from backend.database.entities import RednetMessage
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


class RednetCollector(PlaywrightCollectorBase):
    """红网采集器（湖南地方新闻）"""

    def __init__(self, config: Dict[str, Any]):
        """初始化采集器"""
        super().__init__(config)

        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.source_id = config.get('id', 'auto')

        self.url = config['config'].get('url', 'https://hn.rednet.cn/')
        self.region = config['config'].get('region', '中国')
        self.language = config['config'].get('language', 'zh')
        self.max_articles = config['config'].get('max_articles', 20)

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【红网】ChromaDB不可用")

        if _llm_available:
            self.embedding_client = get_embedding_client()
        else:
            self.embedding_client = None
            logger.warning("【红网】Embedding服务不可用")

        if _field_enricher_available:
            self.field_enricher = get_field_enricher()
        else:
            self.field_enricher = None
            logger.warning("【红网】FieldEnricher不可用")

    async def _on_initialize(self) -> bool:
        """初始化ChromaDB collection"""
        try:
            if self.chroma_storage:
                self.chroma_storage.create_collection(
                    collection_name=self.chroma_collection
                )
            logger.info(f"【红网】采集器初始化成功")
            return True
        except Exception as e:
            logger.error(f"【红网】初始化失败: {e}")
            return False

    async def _collect_once(self) -> None:
        """单次采集（三阶段架构）"""
        try:
            existing_urls = await self._get_existing_urls()
            logger.info(f"【红网】已存在 {len(existing_urls)} 条URL")

            articles = await self._scrape_articles(existing_urls)
            if not articles:
                logger.info("【红网】无新文章")
                return

            logger.info(f"【红网】采集到 {len(articles)} 篇新文章")

            # 阶段2：字段补全
            enriched_articles = await self._enrich_fields(articles)

            # 阶段3：存储
            await self._store_articles(enriched_articles)

            logger.info(f"【红网】本轮采集完成，新增 {len(enriched_articles)} 篇")

        except Exception as e:
            logger.error(f"【红网】采集失败: {e}", exc_info=True)
            raise

    async def _get_existing_urls(self) -> set:
        """获取数据库中已存在的URL"""
        try:
            with create_session() as db:
                results = db.query(RednetMessage.url).all()
                return {row[0] for row in results}
        except Exception as e:
            logger.error(f"【红网】获取已存在URL失败: {e}")
            return set()

    async def _scrape_articles(self, existing_urls: set) -> List[Dict[str, Any]]:
        """阶段1：网页抓取"""
        articles = []
        page = None

        try:
            page = await self._browser.new_page()

            logger.info(f"【红网】访问: {self.url}")
            await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)

            # 提取新闻链接（使用h3 a选择器）
            links = await page.query_selector_all('h3 a')
            logger.info(f"【红网】找到 {len(links)} 个新闻链接")

            for link in links[:self.max_articles]:
                try:
                    href = await link.get_attribute('href')
                    title = await link.inner_text()

                    if not href or not title:
                        continue

                    # 处理相对链接
                    if href.startswith('/'):
                        href = f"https://hn.rednet.cn{href}"
                    elif not href.startswith('http'):
                        href = f"https://hn.rednet.cn/{href}"

                    # 跳过已存在的URL
                    if href in existing_urls:
                        logger.debug(f"【红网】跳过已存在URL: {href}")
                        continue

                    articles.append({
                        'url': href,
                        'title': title.strip(),
                        'provider': '红网',
                    })

                except Exception as e:
                    logger.warning(f"【红网】提取链接失败: {e}")
                    continue

        except Exception as e:
            logger.error(f"【红网】抓取失败: {e}", exc_info=True)
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
                logger.info(f"【红网】补全字段 ({i}/{len(articles)}): {article['title'][:30]}")

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

                # 如果有field_enricher，使用LLM生成summary
                if self.field_enricher and content:
                    try:
                        article['summary'] = await self.field_enricher.generate_summary(content)
                    except Exception as e:
                        logger.warning(f"【红网】LLM摘要生成失败: {e}")
                        article['summary'] = content[:200] if content else ""
                else:
                    article['summary'] = content[:200] if content else ""

                enriched.append(article)

            except Exception as e:
                logger.error(f"【红网】字段补全失败 {article['url']}: {e}")
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
                '[class*="content"]',
                'article',
                '.text'
            ]

            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and len(text) > 100:
                        return text.strip()

            # 如果都没找到，返回body文本
            body = await page.query_selector('body')
            if body:
                return (await body.inner_text()).strip()[:2000]

        except Exception as e:
            logger.warning(f"【红网】提取正文失败: {e}")

        return ""

    async def _extract_publish_time(self, page: Page) -> datetime:
        """从详情页提取发布时间"""
        try:
            # 尝试多种时间选择器
            selectors = [
                '.time',
                '.publish-time',
                '[class*="time"]',
                '[class*="date"]'
            ]

            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    time_text = await element.inner_text()
                    # 解析时间文本
                    parsed_time = self._parse_time(time_text)
                    if parsed_time:
                        return parsed_time

        except Exception as e:
            logger.warning(f"【红网】提取时间失败: {e}")

        return datetime.now()

    def _parse_time(self, time_text: str) -> Optional[datetime]:
        """解析时间字符串"""
        try:
            # 常见格式：2025-12-10 14:30、2025/12/10、12月10日等
            patterns = [
                r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{1,2})',
                r'(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{1,2})',
                r'(\d{4})-(\d{1,2})-(\d{1,2})',
                r'(\d{4})/(\d{1,2})/(\d{1,2})',
            ]

            for pattern in patterns:
                match = re.search(pattern, time_text)
                if match:
                    groups = match.groups()
                    if len(groups) == 5:
                        return datetime(int(groups[0]), int(groups[1]), int(groups[2]),
                                      int(groups[3]), int(groups[4]))
                    elif len(groups) == 3:
                        return datetime(int(groups[0]), int(groups[1]), int(groups[2]))

        except Exception as e:
            logger.warning(f"【红网】时间解析失败: {e}")

        return None

    async def _store_articles(self, articles: List[Dict[str, Any]]) -> None:
        """阶段3：存储到MySQL和ChromaDB"""
        for article in articles:
            try:
                # 存储到MySQL
                message_id = str(uuid.uuid4())
                with create_session() as db:
                    msg = RednetMessage(
                        id=message_id,
                        title=article['title'],
                        content=article.get('content', ''),
                        summary=article.get('summary', ''),
                        url=article['url'],
                        provider=article['provider'],
                        published_at=article.get('published_at', datetime.now()),
                        created_at=datetime.now()
                    )
                    db.add(msg)
                    db.commit()

                logger.info(f"【红网】已存储: {article['title'][:30]}")

                # 存储到ChromaDB（如果可用）
                if self.chroma_storage and self.embedding_client and article.get('content'):
                    try:
                        embedding = self.embedding_client.generate_embedding(
                            f"{article['title']} {article['content'][:500]}"
                        )
                        self.chroma_storage.add_documents(
                            collection_name=self.chroma_collection,
                            ids=[message_id],
                            documents=[article['content']],
                            metadatas=[{
                                'title': article['title'],
                                'url': article['url'],
                                'provider': article['provider'],
                                'published_at': article['published_at'].isoformat()
                            }],
                            embeddings=[embedding]
                        )
                    except Exception as e:
                        logger.warning(f"【红网】ChromaDB存储失败: {e}")

            except IntegrityError:
                logger.debug(f"【红网】跳过重复URL: {article['url']}")
            except Exception as e:
                logger.error(f"【红网】存储失败: {e}", exc_info=True)
