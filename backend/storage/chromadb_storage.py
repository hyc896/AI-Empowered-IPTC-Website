# -*- coding: utf-8 -*-

"""
ChromaDB Vector Storage
Simplified from MineContext, focuses on PersonalAgent use cases
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
                - collection_prefix: Collection名称前缀

        Returns:
            是否初始化成功
        """
        try:
            mode = config.get('mode', 'local')
            # 移除collection_prefix，直接使用collection名称

            if mode == 'server':
                # 服务器模式
                host = config.get('host', 'localhost')
                port = config.get('port', 11522)
                logger.info(f"【ChromaDB】服务器模式初始化: {host}:{port}")
                self._client = chromadb.HttpClient(host=host, port=port)
            else:
                # 本地持久化模式
                path = config.get('path', './data/chromadb')
                logger.info(f"【ChromaDB】本地模式初始化: {path}")
                self._client = chromadb.PersistentClient(path=path)

            # 创建消息平台专用Collections
            collection_names = ['tonghuashun', 'kr36', 'arxiv']
            for name in collection_names:
                # 直接使用collection名称，不加前缀
                collection = self._client.get_or_create_collection(
                    name=name,
                    metadata={"hnsw:space": "cosine"}  # 余弦相似度
                )
                self._collections[name] = collection
                logger.info(f"【ChromaDB】Collection 已创建: {name}")

            self._initialized = True
            logger.info("【ChromaDB】向量数据库初始化成功")
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
            logger.warning(f"Collection '{collection_name}' already exists")
            return True

        try:
            collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            self._collections[collection_name] = collection
            logger.info(f"Collection created: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            return False
