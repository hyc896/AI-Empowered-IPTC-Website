# -*- coding: utf-8 -*-

"""
人民网上海红色教育频道采集器
数据来源：http://sh.people.com.cn/GB/138654/（党建）等
特点：传统HTML，GBK编码，用 requests 直接抓取，无需 Playwright
"""

import uuid
import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.exc import IntegrityError

from backend.database.entities import PeopleShRedMessage
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

# 红色教育关键词过滤（只保留相关文章）
RED_KEYWORDS = [
    '红色', '党史', '党建', '革命', '烈士', '纪念', '爱国', '初心', '使命',
    '中共', '共产党', '党员', '党委', '党支部', '学习教育', '主题教育',
    '红色文化', '红色基地', '红色旅游', '红色资源', '红色精神',
    '抗战', '解放', '建党', '建国', '长征', '延安',
    '习近平', '毛泽东', '周恩来', '邓小平',
]


def _contains_red_keyword(text: str) -> bool:
    return any(kw in text for kw in RED_KEYWORDS)


class PeopleShRedCollector(PlaywrightCollectorBase):
    """人民网上海红色教育采集器（requests模式，不依赖浏览器）"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.source_id = config.get('id', 'auto')
        self.urls = config['config'].get('urls', ['http://sh.people.com.cn/GB/138654/index.html'])
        self.base_url = config['config'].get('base_url', 'http://sh.people.com.cn')
        self.region = config['config'].get('region', '中国/上海')
        self.language = config['config'].get('language', 'zh')
        self.max_articles = config['config'].get('max_articles', 20)

        self.chroma_storage = get_chromadb_storage() if _chroma_available else None
        self.embedding_client = get_embedding_client() if _llm_available else None
        self.field_enricher = get_field_enricher() if _field_enricher_available else None

        import requests as req
        self._session = req.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        })

    async def _on_initialize(self) -> bool:
        try:
            if self.chroma_storage:
                self.chroma_storage.create_collection(collection_name=self.chroma_collection)
            logger.info("【人民网上海红色】采集器初始化成功")
            return True
        except Exception as e:
            logger.error(f"【人民网上海红色】初始化失败: {e}")
            return False

    async def _collect_once(self) -> None:
        try:
            existing_urls = await self._get_existing_urls()
            articles = await self._scrape_articles(existing_urls)
            if not articles:
                logger.debug("【人民网上海红色】没有发现新文章")
                return
            logger.info(f"【人民网上海红色】抓取到 {len(articles)} 篇新文章")
            await self._preprocess_items(articles)
            await self._store_items(articles)
            logger.info(f"【人民网上海红色】采集完成，共处理 {len(articles)} 篇文章")
        except Exception as e:
            logger.error(f"【人民网上海红色】采集错误: {e}", exc_info=True)

    async def _get_existing_urls(self, limit: int = 1000) -> set:
        try:
            with create_session() as db:
                results = db.query(PeopleShRedMessage.url).filter(
                    PeopleShRedMessage.source_id == self.source_id,
                    PeopleShRedMessage.url.isnot(None)
                ).order_by(PeopleShRedMessage.crawled_at.desc()).limit(limit).all()
                return {str(row[0]) for row in results if row[0]}
        except Exception as e:
            logger.error(f"【人民网上海红色】获取existing_urls失败: {e}")
            return set()

    async def _scrape_articles(self, existing_urls: set) -> List[Dict[str, Any]]:
        from bs4 import BeautifulSoup
        articles = []
        candidates = []

        # 阶段1：从各列表页收集候选链接
        for list_url in self.urls:
            try:
                resp = await asyncio.get_event_loop().run_in_executor(
                    None, lambda u=list_url: self._session.get(u, timeout=10)
                )
                soup = BeautifulSoup(resp.content, 'html.parser', from_encoding='gbk')

                for ul in soup.find_all('ul', class_='list_16'):
                    for li in ul.find_all('li'):
                        a = li.find('a')
                        if not a:
                            continue
                        href = a.get('href', '')
                        title = a.get_text(strip=True)
                        if not href or not title:
                            continue

                        # 补全URL
                        if href.startswith('/'):
                            href = self.base_url + href
                        elif not href.startswith('http'):
                            continue

                        if href in existing_urls:
                            continue

                        # 关键词过滤：只保留红色教育相关
                        if not _contains_red_keyword(title):
                            continue

                        # 提取发布时间（从URL中的日期）
                        date_match = re.search(r'/(\d{4})/(\d{4})/', href)
                        if date_match:
                            try:
                                published_at = datetime.strptime(
                                    f"{date_match.group(1)}{date_match.group(2)}", "%Y%m%d"
                                )
                            except Exception:
                                published_at = datetime.now()
                        else:
                            published_at = datetime.now()

                        external_id = re.search(r'c\d+-(\d+)\.html', href)
                        external_id = external_id.group(1) if external_id else href.split('/')[-1]

                        candidates.append({
                            'url': href,
                            'title': title,
                            'published_at': published_at,
                            'external_id': external_id,
                        })

                logger.info(f"【人民网上海红色】从 {list_url} 收集到 {len(candidates)} 条候选")
            except Exception as e:
                logger.error(f"【人民网上海红色】列表页抓取失败 {list_url}: {e}")

        # 阶段2：抓取正文
        for item in candidates:
            if len(articles) >= self.max_articles:
                break
            content = await self._fetch_content(item['url'])
            if not content:
                continue
            articles.append({
                'external_id': item['external_id'],
                'title': item['title'],
                'content': content,
                'summary': content[:200],
                'url': item['url'],
                'published_at': item['published_at'],
                'provider': '人民网上海',
                'language': self.language,
                'category': '红色教育',
            })
            await asyncio.sleep(0.5)

        return articles

    async def _fetch_content(self, url: str) -> str:
        from bs4 import BeautifulSoup
        try:
            resp = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._session.get(url, timeout=10)
            )
            soup = BeautifulSoup(resp.content, 'html.parser', from_encoding='gbk')

            for selector in [
                {'class': 'rm_txt_con'},
                {'class': 'article'},
                {'id': 'rwb_zw'},
                {'class': 'text_con'},
            ]:
                el = soup.find(attrs=selector)
                if el:
                    paragraphs = el.find_all('p')
                    if paragraphs:
                        texts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
                        if texts:
                            return '\n\n'.join(texts)
                    text = el.get_text(strip=True)
                    if text:
                        return text
            return ""
        except Exception as e:
            logger.error(f"【人民网上海红色】获取正文失败 {url}: {e}")
            return ""

    async def _preprocess_items(self, items: List[Dict[str, Any]]) -> None:
        for idx, item in enumerate(items, 1):
            item['message_id'] = str(uuid.uuid4())
            try:
                if self.field_enricher:
                    enriched = await self.field_enricher.enrich_fields(
                        title=item['title'], content=item['content'], message_id=item['message_id']
                    )
                    item['region'] = enriched.get('region', self.region)
                    item['industry_tags'] = enriched.get('industry_tags')
                    item['ai_tag'] = enriched.get('ai_tag')
                else:
                    item['region'] = self.region
                    item['industry_tags'] = None
                    item['ai_tag'] = None
            except Exception as e:
                logger.error(f"【人民网上海红色】预处理失败 [{idx}]: {e}")
                item['region'] = self.region
                item['industry_tags'] = None
                item['ai_tag'] = None

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        await self._store_to_mysql(items)
        await self._store_to_chroma(items)

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> None:
        try:
            with create_session() as db:
                for item in items:
                    msg = PeopleShRedMessage(
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
                        db.add(msg)
                        db.commit()
                    except IntegrityError as e:
                        db.rollback()
                        if "Duplicate entry" not in str(e):
                            logger.error(f"【人民网上海红色】MySQL存储错误: {e}")
        except Exception as e:
            logger.error(f"【人民网上海红色】MySQL存储失败: {e}")

    async def _store_to_chroma(self, items: List[Dict[str, Any]]) -> None:
        if not self.chroma_storage or not self.embedding_client:
            return
        try:
            for item in items:
                doc = f"{item['title']} {item.get('summary', '')}"
                embedding = self.embedding_client.generate_embedding(doc)
                chroma_id = item.get('external_id') or str(uuid.uuid4())
                self.chroma_storage.upsert(
                    collection_name=self.chroma_collection,
                    ids=[chroma_id],
                    documents=[doc],
                    metadatas=[{
                        "source_id": self.source_id,
                        "external_id": item.get('external_id', ''),
                        "published_at": item['published_at'].isoformat() if item.get('published_at') else '',
                        "url": item.get('url', ''),
                        "title": item['title'],
                        "region": item.get('region', ''),
                        "language": item.get('language', '')
                    }],
                    embeddings=[embedding]
                )
        except Exception as e:
            logger.error(f"【人民网上海红色】ChromaDB存储失败: {e}")
