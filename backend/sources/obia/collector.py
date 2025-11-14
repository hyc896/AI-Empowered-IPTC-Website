# -*- coding: utf-8 -*-

"""
OBIA (Observatório Brasileiro de Inteligência Artificial) Collector
巴西AI观测站（巴西）研究出版物采集器
"""

import re
import uuid
import asyncio
import logging
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError

from backend.database.entities import OBIAMessage
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

logger = logging.getLogger(__name__)


class OBIACollector:
    """OBIA研究出版物采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - url: OBIA出版物页URL
                - source_id: 消息源ID（关联message_sources表）
                - region: 地区（BR=Brazil）
                - language: 语言（pt=葡萄牙语）
        """
        self.config = config
        self.interval = config.get('interval', 86400)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.url = config['config'].get('url', 'https://obia.nic.br/s/publicacoes')
        self.source_id = config.get('id', 'auto')
        self.region = config['config'].get('region', 'BR')
        self.language = config['config'].get('language', 'pt')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【OBIA】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【OBIA】LLM服务不可用，将跳过向量化和翻译")

        self._running = False
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        })

    async def initialize(self) -> bool:
        """
        初始化采集器

        Returns:
            是否初始化成功
        """
        try:
            if self.chroma_storage:
                self.chroma_storage.create_collection(
                    collection_name=self.chroma_collection
                )

            logger.info(f"【OBIA】采集器初始化成功: {self.url}")
            return True
        except Exception as e:
            logger.error(f"【OBIA】采集器初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每隔interval秒执行一次采集
        """
        if not await self.initialize():
            logger.error("【OBIA】采集器初始化失败，退出")
            return

        self._running = True
        logger.info(f"【OBIA】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【OBIA】采集失败: {e}")

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        self.session.close()
        logger.info("【OBIA】采集器已停止")

    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新出版物URL
        2. 使用requests爬取出版物列表页
        3. 过滤已存在URL
        4. 预翻译所有摘要（避免数据库会话阻塞）
        5. 并发存储到MySQL + ChromaDB
        """
        try:
            latest_url = await self._get_latest_stored_url()
            logger.debug(f"Latest stored URL: {latest_url}")

            publications_list = await self._scrape_publications_list(latest_url)

            if not publications_list:
                logger.debug("No new items to collect")
                return

            new_items = self._filter_new_items(publications_list, latest_url)

            if new_items:
                # 预翻译所有摘要（在数据库会话之外）
                logger.info(f"【OBIA】开始翻译 {len(new_items)} 篇出版物的摘要...")
                await self._pretranslate_summaries(new_items)

                await self._store_items(new_items)
                logger.info(f"【OBIA】采集到 {len(new_items)} 篇新出版物")
            else:
                logger.debug("【OBIA】所有出版物已存在，无新数据")

        except Exception as e:
            logger.error(f"【OBIA】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新出版物的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(OBIAMessage).filter(
                    OBIAMessage.source_id == self.source_id,
                    OBIAMessage.url.isnot(None)
                ).order_by(
                    OBIAMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL: {e}")
            return None

    async def _scrape_publications_list(self, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        使用requests爬取出版物列表页

        Args:
            latest_url: 最新已存储的URL，遇到此URL立即停止

        Returns:
            出版物列表
        """
        try:
            response = self.session.get(self.url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'

            soup = BeautifulSoup(response.text, 'html.parser')

            # 查找所有出版物条目（使用.publicacao[data-guid]选择器）
            publication_elements = soup.select('div.publicacao[data-guid]')
            logger.debug(f"Found {len(publication_elements)} publication elements")

            publications_list = []
            for pub_elem in publication_elements:
                pub_data = self._extract_publication_data(pub_elem)

                if not pub_data:
                    continue

                pub_url = pub_data.get('url')
                if not pub_url:
                    continue

                # 停止条件：遇到最新已存储的URL
                if latest_url and pub_url == latest_url:
                    logger.debug(f"Reached latest stored URL ({latest_url}), stopping")
                    break

                publications_list.append(pub_data)

            return publications_list

        except Exception as e:
            logger.error(f"Failed to scrape publications list: {e}", exc_info=True)
            return []

    def _extract_publication_data(self, pub_elem) -> Optional[Dict[str, Any]]:
        """
        从出版物元素中提取数据

        Args:
            pub_elem: BeautifulSoup元素（<div class="publicacao">）

        Returns:
            出版物数据字典
        """
        try:
            # 提取data-guid作为external_id
            external_id = pub_elem.get('data-guid')

            # 提取PDF链接
            link_elem = pub_elem.select_one('a.view-publicacao_link_bloco[href]')
            if not link_elem:
                return None

            pdf_url = link_elem.get('href')
            if not pdf_url:
                return None

            # 补全相对URL
            if pdf_url.startswith('/'):
                pdf_url = f"https://obia.nic.br{pdf_url}"
            elif not pdf_url.startswith('http'):
                pdf_url = f"https://cetic.br{pdf_url}"

            # 提取分类（PANORAMA SETORIAL DA INTERNET / PESQUISAS TIC）
            category_elem = pub_elem.select_one('.publicacao-content-texto > div > p')
            category = category_elem.get_text(strip=True) if category_elem else None

            # 提取标题
            title_elem = pub_elem.select_one('.publicacao-content-texto > div > h1')
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)

            # 提取描述（包含作者信息）
            desc_elem = pub_elem.select_one('.publicacao-content-texto > div > div')
            description = ""
            authors = []
            if desc_elem:
                # 描述文本
                description = desc_elem.get_text(strip=True)

                # 提取作者（em标签）
                author_elems = desc_elem.select('em')
                for author_elem in author_elems:
                    author_text = author_elem.get_text(strip=True)
                    if author_text and len(author_text) > 0:
                        # 拆分多个作者（分号或逗号分隔）
                        author_names = re.split(r'[;,]', author_text)
                        authors.extend([name.strip() for name in author_names if name.strip()])

            provider = ", ".join(authors) if authors else None

            # 从PDF URL中提取发布时间
            published_at = self._extract_date_from_url(pdf_url)

            # 从标题中提取系列名称
            series = self._extract_series_from_title(title)

            return {
                "external_id": external_id,
                "title": title,
                "content": description if description else title,
                "summary": None,  # 将在预翻译阶段生成
                "provider": provider,
                "published_at": published_at,
                "url": pdf_url,
                "region": self.region,
                "category": category,
                "language": self.language,
                "pdf_url": pdf_url,
                "series": series
            }
        except Exception as e:
            logger.error(f"Failed to extract publication data: {e}")
            return None

    def _extract_date_from_url(self, url: str) -> datetime:
        """
        从PDF URL中提取发布时间

        Args:
            url: PDF URL，如 https://cetic.br/media/docs/publicacoes/6/20200626161010/...

        Returns:
            datetime对象
        """
        try:
            # 匹配URL中的14位时间戳（YYYYMMDDhhmmss）
            match = re.search(r'/(\d{14})/', url)
            if match:
                timestamp_str = match.group(1)
                # 解析为datetime
                return datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')

            # 如果没有14位时间戳，尝试8位日期（YYYYMMDD）
            match = re.search(r'/(\d{8})\d{6}/', url)
            if match:
                date_str = match.group(1)
                return datetime.strptime(date_str, '%Y%m%d')

            logger.warning(f"Failed to extract date from URL: {url}")
            return datetime.now()
        except Exception as e:
            logger.error(f"Failed to parse date from URL '{url}': {e}")
            return datetime.now()

    def _extract_series_from_title(self, title: str) -> Optional[str]:
        """
        从标题中提取系列名称

        Args:
            title: 标题文本

        Returns:
            系列名称
        """
        # 常见系列名称模式
        series_patterns = [
            r'^(Panorama Setorial)',
            r'^(TIC\s+\w+)',  # TIC Empresas, TIC Governo, TIC Educação等
            r'^(Inteligência Artificial)',
        ]

        for pattern in series_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _filter_new_items(
        self,
        publications_list: List[Dict[str, Any]],
        latest_url: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        过滤已存在的出版物

        Args:
            publications_list: 出版物列表
            latest_url: 最新已存储URL

        Returns:
            新出版物列表
        """
        if not latest_url:
            return publications_list

        new_items = []
        for item in publications_list:
            if item.get('url') == latest_url:
                break
            new_items.append(item)

        return new_items

    async def _pretranslate_summaries(self, items: List[Dict[str, Any]]) -> None:
        """
        预翻译所有出版物的摘要（在数据库会话之外）

        Args:
            items: 出版物列表
        """
        if not self.translator:
            logger.warning("【OBIA】翻译器不可用，跳过翻译")
            return

        for idx, item in enumerate(items, 1):
            try:
                summary = await self._generate_summary(
                    item.get('summary'),
                    item.get('content', '')
                )
                item['summary'] = summary
                logger.debug(f"[{idx}/{len(items)}] ✓ 翻译完成: {item.get('title')}")
            except Exception as e:
                logger.error(f"[{idx}/{len(items)}] ✗ 翻译失败: {e}")
                # 降级策略：使用截断原文
                content = item.get('content', '')
                item['summary'] = content[:500] + "... [AI翻译暂不可用]" if len(content) > 500 else content

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        """
        并发存储到MySQL和ChromaDB

        Args:
            items: 出版物列表
        """
        mysql_task = self._store_to_mysql(items)
        chroma_task = self._store_to_chroma(items)
        await asyncio.gather(mysql_task, chroma_task, return_exceptions=True)

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到MySQL

        Args:
            items: 出版物列表
        """
        try:
            with create_session() as db:
                for item in items:
                    message = OBIAMessage(
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
                        category=item.get('category'),
                        language=item.get('language'),
                        pdf_url=item.get('pdf_url'),
                        series=item.get('series')
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
            items: 出版物列表
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
                        "region": item.get('region', ''),
                        "category": item.get('category', ''),
                        "language": item.get('language', ''),
                        "series": item.get('series', '')
                    }],
                    embeddings=[embedding]
                )
                logger.debug(f"Inserted to ChromaDB: url={item.get('url')}")
        except Exception as e:
            logger.error(f"Failed to store to ChromaDB: {e}")

    async def _generate_summary(self, summary: Optional[str], content: str) -> str:
        """
        生成摘要（支持葡萄牙语到中文翻译）

        葡萄牙语内容自动翻译成中文

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
        if self._is_chinese(source_text):
            # 中文内容：直接返回或截断
            if len(source_text) <= 1000:
                return source_text
            return source_text[:1000] + "..."

        # 3. 葡萄牙语内容：翻译成中文
        if self.translator:
            try:
                # 全文翻译（不限制长度，由translator内部处理）
                translated = await self.translator.translate(
                    source_text,
                    context="OBIA巴西AI观测站研究出版物摘要"
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
