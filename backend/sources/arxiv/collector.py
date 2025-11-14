# -*- coding: utf-8 -*-

"""
arXiv Collector
arXiv学术论文采集器
"""

import uuid
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

try:
    import arxiv
except ImportError:
    arxiv = None

from sqlalchemy.exc import IntegrityError

from backend.database.entities import ArxivMessage, MessageSource
from backend.database.connection import create_session
try:
    from backend.storage import get_chromadb_storage
    _chroma_available = True
except ImportError:
    _chroma_available = False

try:
    from backend.llm import get_embedding_client, get_fast_client
    _llm_available = True
except ImportError:
    _llm_available = False

logger = logging.getLogger(__name__)


class ArxivCollector:
    """arXiv学术论文采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - id: 消息源ID
                - config: 详细配置
                  - interval: 采集间隔（秒）
                  - mysql_table: MySQL表名
                  - chroma_collection: ChromaDB collection名称
                  - categories: 关注的分类列表
                  - max_results_per_category: 每个分类最大抓取数量
                  - date_range_days: 抓取时间范围（天）
                  - summary_length_threshold: 摘要长度阈值
        """
        if arxiv is None:
            raise ImportError("arxiv库未安装，请运行: pip install arxiv")

        self.source_id = config['id']
        self.interval = config['config'].get('interval', 86400)
        self.mysql_table = config['config']['mysql_table']
        self.chroma_collection = config['config']['chroma_collection']
        self.summary_threshold = config['config'].get('summary_length_threshold', 1000)

        # 优雅地处理缺失的依赖
        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【arXiv】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
        else:
            self.embedding_client = None
            logger.warning("【arXiv】Embedding服务不可用，将跳过向量化")

        self.client = arxiv.Client()
        self._running = False
        self._is_first_run = True

    async def initialize(self) -> bool:
        """
        初始化采集器

        Returns:
            是否初始化成功
        """
        try:
            # 创建 ChromaDB collection
            self.chroma_storage.create_collection(
                collection_name=self.chroma_collection
            )
            return True
        except Exception as e:
            logger.error(f"【arXiv】初始化失败: {e}")
            return False

    async def run(self) -> None:
        """
        主循环：定时采集

        每次采集前从数据库重新读取配置，实现动态配置
        """
        if not await self.initialize():
            logger.error("【arXiv】初始化失败，退出")
            return

        self._running = True

        while self._running:
            try:
                # 从数据库重新读取配置
                current_config = self._load_config_from_db()
                if current_config:
                    await self.fetch_and_store(current_config)
                else:
                    logger.warning(f"【arXiv】无法加载配置，跳过本次采集")

                await asyncio.sleep(self.interval)
            except Exception as e:
                logger.error(f"【arXiv】采集失败: {e}", exc_info=True)
                await asyncio.sleep(self.interval)

    def _load_config_from_db(self) -> Optional[Dict[str, Any]]:
        """
        从数据库重新加载最新配置

        Returns:
            配置字典或None
        """
        try:
            with create_session() as db:
                source = db.query(MessageSource).filter(
                    MessageSource.id == self.source_id
                ).first()

                if not source or not source.is_active:
                    return None

                return source.config
        except Exception as e:
            logger.error(f"【arXiv】加载配置失败: {e}")
            return None

    async def fetch_and_store(self, config: Dict[str, Any]) -> None:
        """
        根据当前配置抓取论文

        Args:
            config: 配置字典
        """
        categories = config.get('categories', [])
        max_results = config.get('max_results_per_category', 50)
        date_range_days = config.get('date_range_days', 7)

        if self._is_first_run:
            date_range_days = 30
            self._is_first_run = False

        if not categories:
            logger.warning(f"【arXiv】未配置分类，跳过采集")
            return

        # 计算日期范围（arXiv API要求格式：YYYYMMDDhhmm，并且需要明确的结束日期）
        date_from = datetime.now() - timedelta(days=date_range_days)
        date_to = datetime.now()
        date_from_str = date_from.strftime('%Y%m%d%H%M')
        date_to_str = date_to.strftime('%Y%m%d%H%M')

        logger.info(f"【arXiv】开始采集: {', '.join(categories)} ({date_range_days}天)")

        total_saved = 0
        total_skipped = 0

        for category in categories:
            try:
                saved, skipped = await self._fetch_category(
                    category, date_from_str, date_to_str, max_results
                )
                total_saved += saved
                total_skipped += skipped

                # 遵守 arXiv API 速率限制（每3秒1次请求）
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"【arXiv】抓取分类 {category} 失败: {e}", exc_info=True)

        if total_saved > 0:
            logger.info(f"【arXiv】采集完成: 新增{total_saved}篇 ✓")

        # 更新last_crawled_at
        self._update_last_crawled()

    async def _fetch_category(
        self, category: str, date_from: str, date_to: str, max_results: int
    ) -> tuple[int, int]:
        """
        抓取单个分类的论文

        Args:
            category: 分类代码（如 cs.AI）
            date_from: 起始日期（YYYYMMDDhhmm格式）
            date_to: 结束日期（YYYYMMDDhhmm格式）
            max_results: 最大结果数

        Returns:
            (保存数量, 跳过数量)
        """
        query = f"cat:{category} AND submittedDate:[{date_from} TO {date_to}]"
        logger.debug(f"【arXiv】查询语句: {query}, max_results={max_results}")

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )

        saved_count = 0
        skipped_count = 0

        try:
            results_generator = self.client.results(search)
            papers_processed = 0

            try:
                for paper in results_generator:
                    papers_processed += 1
                    try:
                        if await self._save_paper(paper):
                            saved_count += 1
                        else:
                            skipped_count += 1
                    except Exception as e:
                        logger.error(f"【arXiv】保存论文失败: {e}", exc_info=True)
                        skipped_count += 1


            except arxiv.UnexpectedEmptyPageError as e:
                logger.warning(f"【arXiv】{category}: API分页异常，已处理{papers_processed}篇")

        except Exception as e:
            logger.error(f"【arXiv】{category}: 查询失败 - {e}")

        if saved_count > 0 or skipped_count > 0:
            logger.info(f"【arXiv】{category}: {saved_count}篇新增, {skipped_count}篇重复")
        return saved_count, skipped_count

    async def _save_paper(self, paper) -> bool:
        """
        保存单篇论文到MySQL和ChromaDB

        Args:
            paper: arxiv.Result对象

        Returns:
            是否保存成功
        """
        with create_session() as db:
            # 提取 arxiv_id
            arxiv_id = paper.entry_id.split('/')[-1]

            # 检查是否已存在（去重）
            existing = db.query(ArxivMessage).filter(
                ArxivMessage.arxiv_id == arxiv_id
            ).first()

            if existing:
                return False  # 跳过重复

            # 处理作者
            authors_list = [author.name for author in paper.authors]
            if authors_list:
                provider = ', '.join(authors_list)
            else:
                provider = "Anonymous"

            # 处理摘要
            abstract = paper.summary.strip()
            if len(abstract) < self.summary_threshold:
                summary = abstract
            else:
                # 调用LLM生成简短摘要
                summary = await self._generate_summary(abstract)

            # 生成URL
            url = paper.entry_id  # https://arxiv.org/abs/xxx

            # 创建消息记录
            message = ArxivMessage(
                id=str(uuid.uuid4()),
                source_id=self.source_id,
                arxiv_id=arxiv_id,
                title=paper.title.strip(),
                content=abstract,
                summary=summary,
                provider=provider,
                published_at=paper.published,
                url=url,
                primary_category=paper.primary_category,
                categories=paper.categories,
                doi=paper.doi,
                journal_ref=paper.journal_ref,
                comment=paper.comment,
                updated_at=paper.updated
            )

            try:
                db.add(message)
                db.commit()

                # 向量化并存入ChromaDB
                await self._vectorize_and_store(message)

                logger.info(f"【arXiv】保存论文: {message.title[:50]}...")
                return True

            except IntegrityError:
                db.rollback()
                return False

    async def _generate_summary(self, abstract: str) -> str:
        """
        使用统一翻译器翻译摘要（英文→中文）

        Args:
            abstract: 英文摘要

        Returns:
            中文翻译（或降级返回截断的原文）
        """
        from backend.llm.translator import get_translator

        translator = get_translator()
        return await translator.translate(
            text=abstract,
            context="学术论文摘要"
        )

    async def _vectorize_and_store(self, message: ArxivMessage) -> None:
        """
        向量化论文并存入ChromaDB

        Args:
            message: 论文消息记录
        """
        try:
            # 向量化 title + summary（简短摘要，而非完整abstract）
            document_text = f"{message.title}\n\n{message.summary}"
            embedding = self.embedding_client.generate_embedding(document_text)

            self.chroma_storage.upsert(
                collection_name=self.chroma_collection,
                ids=[message.id],
                documents=[document_text],
                metadatas=[{
                    "arxiv_id": message.arxiv_id,
                    "title": message.title,
                    "primary_category": message.primary_category,
                    "url": message.url,
                    "published_at": message.published_at.isoformat() if message.published_at else ''
                }],
                embeddings=[embedding]
            )
        except Exception as e:
            logger.error(f"【arXiv】向量化失败: {e}")

    def _update_last_crawled(self) -> None:
        """更新最后抓取时间"""
        try:
            with create_session() as db:
                source = db.query(MessageSource).filter(
                    MessageSource.id == self.source_id
                ).first()

                if source:
                    source.last_crawled_at = datetime.now()
                    db.commit()
        except Exception as e:
            logger.error(f"【arXiv】更新抓取时间失败: {e}")

    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        logger.info(f"【arXiv】采集器已停止")
