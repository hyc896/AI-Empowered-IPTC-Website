# -*- coding: utf-8 -*-

"""
中国社会科学网采集器
CSSN Collector

数据来源：http://www.cssn.cn/
特点：中国社会科学院主办的学术新闻网站
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import Browser, Page
from sqlalchemy.exc import IntegrityError

from backend.database.entities import CssnMessage
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


class CssnCollector(PlaywrightCollectorBase):
    """中国社会科学网采集器（国内思政理论新闻）"""

    def __init__(self, config: Dict[str, Any]):
        """初始化采集器"""
        super().__init__(config)

        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.source_id = config.get('id', 'auto')

        self.url = config['config'].get('url', 'http://www.cssn.cn/')
        self.region = config['config'].get('region', '中国')
        self.language = config['config'].get('language', 'zh')
        self.max_articles = config['config'].get('max_articles', 20)

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【中国社科网】ChromaDB不可用")

        if _llm_available:
            self.embedding_client = get_embedding_client()
        else:
            self.embedding_client = None
            logger.warning("【中国社科网】Embedding服务不可用")

        if _field_enricher_available:
            self.field_enricher = get_field_enricher()
        else:
            self.field_enricher = None
            logger.warning("【中国社科网】FieldEnricher不可用")

    async def _on_initialize(self) -> bool:
        """初始化ChromaDB collection"""
        try:
            if self.chroma_storage:
                self.chroma_storage.create_collection(
                    collection_name=self.chroma_collection
                )
            logger.info(f"【中国社科网】采集器初始化成功")
            return True
        except Exception as e:
            logger.error(f"【中国社科网】初始化失败: {e}")
            return False

    async def _collect_once(self) -> None:
        """单次采集（三阶段架构）"""
        try:
            existing_urls = await self._get_existing_urls()
            logger.info(f"【中国社科网】已存在 {len(existing_urls)} 条URL")

            articles = await self._scrape_articles(existing_urls)
            if not articles:
                logger.debug("【中国社科网】无新文章")
                return

            logger.info(f"【中国社科网】抓取到 {len(articles)} 篇新文章")
            await self._preprocess_items(articles)
            await self._store_items(articles)
            logger.info(f"【中国社科网】采集完成")

        except Exception as e:
            logger.error(f"【中国社科网】采集错误: {e}", exc_info=True)

    async def _get_existing_urls(self, limit: int = 1000) -> set:
        """获取已存在URL集合"""
        try:
            with create_session() as db:
                results = db.query(CssnMessage.url).filter(
                    CssnMessage.source_id == self.source_id,
                    CssnMessage.url.isnot(None)
                ).order_by(
                    CssnMessage.crawled_at.desc()
                ).limit(limit).all()
                return {str(row[0]) for row in results if row[0]}
        except Exception as e:
            logger.error(f"【中国社科网】获取existing_urls失败: {e}")
            return set()

    async def _scrape_articles(self, existing_urls: set) -> List[Dict[str, Any]]:
        """抓取文章列表"""
        page: Optional[Page] = None
        articles = []

        try:
            page = await self._browser.new_page()
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            })

            await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)

            logger.info(f"【中国社科网】开始滚动加载...")

            # 尝试多种选择器（通用策略）
            selectors_to_try = [
                # 通用列表选择器
                'ul li',
                'ul li a',
                '[class*="list"] li',
                '[class*="article"] li',
                '[class*="news"] li',

                # 中国社科网特定
                '.news-list li',
                '.article-list li',
                '.news_con li',
                '.list_con li',
                '[class*="item"]',

                # 通用文章容器
                'article',
                'div[class*="list"] a',
                'div[class*="content"] a'
            ]

            selected_selector = None
            for selector in selectors_to_try:
                try:
                    test_elements = await page.query_selector_all(selector)
                    if test_elements and len(test_elements) > 0:
                        selected_selector = selector
                        logger.debug(f"【中国社科网】使用选择器: {selector}")
                        break
                except Exception:
                    continue

            if not selected_selector:
                logger.warning("【中国社科网】未找到文章元素")
                return []

            load_attempts = 0
            max_load_attempts = 10
            consecutive_no_new = 0
            processed_count = 0

            while load_attempts < max_load_attempts and len(articles) < self.max_articles:
                article_elements = await page.query_selector_all(selected_selector)
                current_count = len(article_elements)

                new_found = 0
                for idx in range(processed_count, current_count):
                    if len(articles) >= self.max_articles:
                        break

                    element = article_elements[idx]

                    try:
                        # 提取链接 - 防御性处理避免上下文销毁错误
                        link_element = None
                        try:
                            is_link = await element.evaluate('el => el.tagName.toLowerCase()')
                            if is_link == 'a':
                                link_element = element
                        except:
                            pass

                        if not link_element:
                            try:
                                link_element = await element.query_selector('a')
                            except:
                                continue

                        if not link_element:
                            continue

                        article_url = await link_element.get_attribute('href')
                        if not article_url:
                            continue

                        if article_url.startswith('/'):
                            article_url = f'http://www.cssn.cn{article_url}'
                        elif not article_url.startswith('http'):
                            continue

                        # 去重检查
                        if article_url in existing_urls:
                            logger.debug(f"【中国社科网】遇到已存在URL，停止")
                            return articles

                        # 提取标题
                        title = await link_element.get_attribute('title')
                        if not title:
                            title = await link_element.inner_text()
                        title = title.strip() if title else ""
                        if not title:
                            continue

                        # 发布时间
                        time_element = await element.query_selector('.time, .date, span')
                        published_at = datetime.now()
                        if time_element:
                            time_text = await time_element.inner_text()
                            published_at = self._parse_publish_time(time_text.strip())

                        external_id = self._extract_external_id(article_url)

                        # 获取正文
                        content = await self._fetch_article_content(page, article_url)
                        if not content:
                            continue

                        summary = content[:200] if len(content) > 200 else content

                        articles.append({
                            'external_id': external_id,
                            'title': title,
                            'content': content,
                            'summary': summary,
                            'url': article_url,
                            'published_at': published_at,
                            'provider': '中国社会科学网',
                            'language': self.language,
                            'category': '学术'
                        })

                        existing_urls.add(article_url)
                        new_found += 1
                        await asyncio.sleep(1)

                    except Exception as e:
                        logger.error(f"【中国社科网】提取失败: {e}")
                        continue

                processed_count = current_count

                if new_found == 0:
                    consecutive_no_new += 1
                    if consecutive_no_new >= 3:
                        break
                else:
                    consecutive_no_new = 0

                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(3)
                load_attempts += 1

        except Exception as e:
            logger.error(f"【中国社科网】抓取失败: {e}", exc_info=True)
        finally:
            if page:
                await page.close()

        return articles

    async def _fetch_article_content(self, page: Page, url: str) -> str:
        """获取文章正文"""
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(1)

            content_selectors = [
                '.content',
                '.article-content',
                '.text-content',
                '#content',
                '#article_content',
                'article',
                '.main-content',
                '.article_content'
            ]

            for selector in content_selectors:
                content_element = await page.query_selector(selector)
                if content_element:
                    paragraphs = await content_element.query_selector_all('p')
                    if paragraphs:
                        texts = []
                        for p in paragraphs:
                            text = await p.inner_text()
                            if text and text.strip():
                                texts.append(text.strip())
                        if texts:
                            return '\n\n'.join(texts)

                    text = await content_element.inner_text()
                    if text and text.strip():
                        return text.strip()

            return ""

        except Exception as e:
            logger.error(f"【中国社科网】获取正文失败: {e}")
            return ""

    async def _preprocess_items(self, items: List[Dict[str, Any]]) -> None:
        """预处理：字段增强"""
        if not items:
            return

        logger.info(f"【中国社科网】开始预处理 {len(items)} 条")

        for idx, item in enumerate(items, 1):
            message_id = str(uuid.uuid4())
            item['message_id'] = message_id

            try:
                if self.field_enricher:
                    enriched = await self.field_enricher.enrich_fields(
                        title=item['title'],
                        content=item['content'],
                        message_id=message_id
                    )
                    item['region'] = enriched.get('region', self.region)
                    item['industry_tags'] = enriched.get('industry_tags')
                    item['ai_tag'] = enriched.get('ai_tag')
                else:
                    item['region'] = self.region
                    item['industry_tags'] = None
                    item['ai_tag'] = None

            except Exception as e:
                logger.error(f"【中国社科网】预处理失败: {e}")
                item['region'] = self.region
                item['industry_tags'] = None
                item['ai_tag'] = None

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        """存储"""
        await self._store_to_mysql(items)
        await self._store_to_chroma(items)

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> None:
        """存储到MySQL"""
        try:
            with create_session() as db:
                for item in items:
                    message = CssnMessage(
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
                        ai_tag=item.get('ai_tag'),
                        category=item.get('category'),
                        language=item.get('language')
                    )

                    try:
                        db.add(message)
                        db.commit()
                        logger.debug(f"【中国社科网】MySQL存储成功")
                    except IntegrityError as e:
                        db.rollback()
                        if "Duplicate entry" in str(e):
                            logger.debug(f"【中国社科网】重复URL")

        except Exception as e:
            logger.error(f"【中国社科网】MySQL存储失败: {e}")

    async def _store_to_chroma(self, items: List[Dict[str, Any]]) -> None:
        """存储到ChromaDB"""
        if not self.chroma_storage or not self.embedding_client:
            return

        try:
            for item in items:
                document_text = f"{item['title']} {item.get('summary', '')}"
                embedding = self.embedding_client.generate_embedding(document_text)
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
                        "language": item.get('language', '')
                    }],
                    embeddings=[embedding]
                )

        except Exception as e:
            logger.error(f"【中国社科网】ChromaDB存储失败: {e}")

    def _extract_external_id(self, url: str) -> str:
        """从URL提取external_id"""
        import hashlib
        match = re.search(r'/(\d+)\.shtml', url)
        if not match:
            match = re.search(r't(\d+)_', url)
        if match:
            return match.group(1)
        return hashlib.md5(url.encode()).hexdigest()

    def _parse_publish_time(self, time_text: str) -> datetime:
        """解析发布时间"""
        from dateutil import parser
        try:
            return parser.parse(time_text, fuzzy=True)
        except:
            return datetime.now()
