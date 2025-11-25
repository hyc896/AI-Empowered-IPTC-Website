# -*- coding: utf-8 -*-

"""
ChromaDB Vector Storage
Vector database for semantic message search
"""

import chromadb
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ChromaDBStorage:
    """
    ChromaDB向量存储
    支持多Collection管理（tonghuashun, kr36, arxiv）
    """

    def __init__(self):
        """初始化ChromaDB存储"""
        self._client: Optional[chromadb.Client] = None
        self._collections: Dict[str, chromadb.Collection] = {}
        self._initialized = False

    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        初始化ChromaDB客户端

        Args:
            config: 配置字典，包含：
                - mode: "local" 或 "server"
                - path: 本地模式的存储路径

        Returns:
            是否初始化成功
        """
        try:
            mode = config.get('mode', 'local')

            if mode == 'server':
                # 服务器模式（Celery worker使用）
                host = config.get('host', 'localhost')
                port = config.get('port', 11530)
                logger.info(f"【ChromaDB】服务器模式初始化: {host}:{port}")
                self._client = chromadb.HttpClient(host=host, port=port)
            else:
                # 本地持久化模式（支持环境变量CHROMADB_PATH）
                import os
                path = config.get('path') or os.getenv('CHROMADB_PATH', './data/chromadb')
                logger.info(f"【ChromaDB】本地模式初始化: {path}")
                self._client = chromadb.PersistentClient(path=path)

            # 动态从数据库读取所有激活消息源的collection配置（配置驱动，零硬编码）
            collection_names = []
            try:
                from backend.database.connection import create_session
                from backend.database.entities import MessageSource

                with create_session() as db:
                    active_sources = db.query(MessageSource).filter(
                        MessageSource.is_active == True
                    ).all()

                    if not active_sources:
                        raise RuntimeError("【ChromaDB】未找到激活的消息源，无法初始化collection")

                    for source in active_sources:
                        source_config = source.config or {}
                        chroma_collection = source_config.get('chroma_collection')

                        if chroma_collection:
                            collection_names.append(chroma_collection)
                        else:
                            logger.warning(f"【ChromaDB】消息源 '{source.name}' 缺少chroma_collection配置")

            except Exception as e:
                # Fail Fast：配置错误时拒绝启动，而非降级
                logger.error(f"【ChromaDB】读取消息源配置失败: {e}")
                logger.error("【ChromaDB】请检查：")
                logger.error("  1. 数据库连接是否正常")
                logger.error("  2. mp_message_sources表是否存在")
                logger.error("  3. 消息源是否正确配置chroma_collection字段")
                raise RuntimeError(f"ChromaDB初始化失败，无法读取消息源配置: {e}") from e

            # 创建所有配置的Collections
            for name in collection_names:
                collection = self._client.get_or_create_collection(
                    name=name,
                    metadata={"hnsw:space": "cosine"}  # 余弦相似度
                )
                self._collections[name] = collection

            self._initialized = True
            logger.info(f"✓ ChromaDB初始化成功 ({', '.join(collection_names)})")
            return True

        except Exception as e:
            logger.error(f"【ChromaDB】初始化失败: {e}")
            return False

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    def upsert(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> bool:
        """
        插入或更新向量数据

        Args:
            collection_name: Collection名称（tonghuashun/kr36/arxiv）
            ids: 文档ID列表
            documents: 文档内容列表
            metadatas: 元数据列表
            embeddings: 向量列表

        Returns:
            是否成功
        """
        if not self._initialized:
            logger.error("【ChromaDB】向量数据库未初始化")
            return False

        collection = self._collections.get(collection_name)
        if collection is None:
            logger.error(f"Collection not found: {collection_name}")
            return False

        try:
            collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            logger.debug(f"Upserted {len(ids)} documents to {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert to {collection_name}: {e}")
            return False

    def search(
        self,
        collection_name: str,
        query_embeddings: List[List[float]],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        向量检索

        Args:
            collection_name: Collection名称
            query_embeddings: 查询向量列表
            n_results: 返回结果数量
            where: 过滤条件（元数据过滤）

        Returns:
            检索结果
        """
        if not self._initialized:
            logger.error("【ChromaDB】向量数据库未初始化")
            return {}

        collection = self._collections.get(collection_name)
        if collection is None:
            logger.error(f"Collection not found: {collection_name}")
            return {}

        try:
            results = collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where if where else None
            )
            return results
        except Exception as e:
            logger.error(f"Failed to search {collection_name}: {e}")
            return {}

    def delete(self, collection_name: str, ids: List[str]) -> bool:
        """
        删除文档

        Args:
            collection_name: Collection名称
            ids: 文档ID列表

        Returns:
            是否成功
        """
        if not self._initialized:
            logger.error("【ChromaDB】向量数据库未初始化")
            return False

        collection = self._collections.get(collection_name)
        if collection is None:
            logger.error(f"Collection not found: {collection_name}")
            return False

        try:
            collection.delete(ids=ids)
            logger.debug(f"Deleted {len(ids)} documents from {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete from {collection_name}: {e}")
            return False

    def count(self, collection_name: str) -> int:
        """
        获取Collection中的文档数量

        Args:
            collection_name: Collection名称

        Returns:
            文档数量
        """
        if not self._initialized:
            logger.error("【ChromaDB】向量数据库未初始化")
            return 0

        collection = self._collections.get(collection_name)
        if collection is None:
            logger.error(f"Collection not found: {collection_name}")
            return 0

        try:
            return collection.count()
        except Exception as e:
            logger.error(f"Failed to count {collection_name}: {e}")
            return 0

    def get_by_ids(
        self,
        collection_name: str,
        ids: List[str]
    ) -> Dict[str, Any]:
        """
        根据ID获取文档

        Args:
            collection_name: Collection名称
            ids: 文档ID列表

        Returns:
            文档数据
        """
        if not self._initialized:
            logger.error("【ChromaDB】向量数据库未初始化")
            return {}

        collection = self._collections.get(collection_name)
        if collection is None:
            logger.error(f"Collection not found: {collection_name}")
            return {}

        try:
            results = collection.get(ids=ids)
            return results
        except Exception as e:
            logger.error(f"Failed to get documents from {collection_name}: {e}")
            return {}

    def create_collection(self, collection_name: str) -> bool:
        """
        动态创建新Collection

        Args:
            collection_name: Collection完整名称（直接使用，不添加前缀）

        Returns:
            是否创建成功
        """
        if not self._initialized:
            logger.error("【ChromaDB】向量数据库未初始化")
            return False

        if collection_name in self._collections:
            return True

        try:
            collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            self._collections[collection_name] = collection
            logger.info(f"✓ Collection创建: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            return False

    def delete_collection(self, collection_name: str) -> bool:
        """
        删除指定Collection

        Args:
            collection_name: Collection名称

        Returns:
            是否删除成功
        """
        if not self._initialized:
            logger.error("【ChromaDB】向量数据库未初始化")
            return False

        try:
            # 从_client中删除collection
            self._client.delete_collection(name=collection_name)

            # 从本地缓存中移除
            if collection_name in self._collections:
                del self._collections[collection_name]

            logger.info(f"✓ Collection已删除: {collection_name}")
            return True
        except Exception as e:
            # 如果collection不存在，认为成功
            if "does not exist" in str(e) or "not found" in str(e).lower():
                logger.warning(f"Collection不存在，无需删除: {collection_name}")
                return True
            logger.error(f"删除Collection失败 {collection_name}: {e}")
            return False

    def collection_exists(self, collection_name: str) -> bool:
        """
        检查Collection是否存在

        Args:
            collection_name: Collection名称

        Returns:
            是否存在
        """
        if not self._initialized:
            return False

        try:
            self._client.get_collection(name=collection_name)
            return True
        except Exception:
            return False

    def get_collection_count(self, collection_name: str) -> int:
        """
        获取Collection中的文档数量（先检查是否存在）

        Args:
            collection_name: Collection名称

        Returns:
            文档数量，不存在返回0
        """
        if not self._initialized:
            return 0

        try:
            collection = self._client.get_collection(name=collection_name)
            return collection.count()
        except Exception:
            return 0
