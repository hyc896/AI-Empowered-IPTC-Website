"""
Neo4j存储层

本模块提供Neo4j图数据库的连接管理和基础CRUD操作。
支持同步和异步操作。

主要功能：
- Driver实例管理
- 连接验证（Fail Fast）
- 读写事务封装
- 异步操作支持（ThreadPoolExecutor）
"""

from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase, Driver
from concurrent.futures import ThreadPoolExecutor
import asyncio
import logging

logger = logging.getLogger(__name__)


class Neo4jStorage:
    """Neo4j存储层"""

    def __init__(self):
        """初始化Neo4j存储层"""
        self._driver: Optional[Driver] = None
        self._executor: Optional[ThreadPoolExecutor] = None

    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化Neo4j驱动

        Args:
            config: 配置字典，包含以下字段：
                - uri: Neo4j连接URI（如bolt://localhost:7687）
                - user: 用户名
                - password: 密码
                - database: 数据库名称（默认neo4j）
                - max_connection_pool_size: 连接池大小（默认50）
                - connection_timeout: 连接超时（秒，默认30）

        Raises:
            RuntimeError: 驱动已初始化
            Exception: 连接失败
        """
        if self._driver is not None:
            logger.warning("Neo4j driver already initialized")
            return

        try:
            uri = config.get('uri', 'bolt://localhost:7687')
            user = config.get('user', 'neo4j')
            password = config.get('password')
            database = config.get('database', 'neo4j')
            max_pool_size = config.get('max_connection_pool_size', 50)
            timeout = config.get('connection_timeout', 30)

            if not password:
                raise ValueError("Neo4j password is required")

            self._driver = GraphDatabase.driver(
                uri,
                auth=(user, password),
                max_connection_pool_size=max_pool_size,
                connection_timeout=timeout,
                database=database
            )

            # Fail Fast：立即验证连接
            self._driver.verify_connectivity()

            # 初始化线程池（用于异步操作）
            self._executor = ThreadPoolExecutor(max_workers=10)

            logger.info(f"Neo4j连接验证成功 (uri={uri}, database={database})")

        except Exception as e:
            logger.error(f"Neo4j初始化失败: {e}")
            raise

    def close(self) -> None:
        """关闭驱动和线程池"""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j驱动已关闭")

        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None
            logger.info("Neo4j线程池已关闭")

    def is_initialized(self) -> bool:
        """检查是否已初始化

        Returns:
            bool: 是否已初始化
        """
        return self._driver is not None

    def get_driver(self) -> Driver:
        """获取Driver实例

        Returns:
            Driver: Neo4j驱动实例

        Raises:
            RuntimeError: 驱动未初始化
        """
        if self._driver is None:
            raise RuntimeError("Neo4j driver not initialized. Call initialize() first.")
        return self._driver

    def execute_read(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """执行读事务

        Args:
            query: Cypher查询语句
            parameters: 查询参数字典

        Returns:
            List[Dict]: 查询结果列表

        Raises:
            RuntimeError: 驱动未初始化
        """
        if not self.is_initialized():
            raise RuntimeError("Neo4j driver not initialized")

        def read_tx(tx):
            result = tx.run(query, parameters or {})
            return [record.data() for record in result]

        with self._driver.session() as session:
            return session.execute_read(read_tx)

    def execute_write(self, query: str, parameters: Optional[Dict] = None) -> Dict:
        """执行写事务

        Args:
            query: Cypher查询语句
            parameters: 查询参数字典

        Returns:
            Dict: 统计信息，包含：
                - nodes_created: 创建的节点数
                - nodes_deleted: 删除的节点数
                - relationships_created: 创建的关系数
                - relationships_deleted: 删除的关系数
                - properties_set: 设置的属性数

        Raises:
            RuntimeError: 驱动未初始化
        """
        if not self.is_initialized():
            raise RuntimeError("Neo4j driver not initialized")

        def write_tx(tx):
            result = tx.run(query, parameters or {})
            summary = result.consume()
            counters = summary.counters
            return {
                "nodes_created": counters.nodes_created,
                "nodes_deleted": counters.nodes_deleted,
                "relationships_created": counters.relationships_created,
                "relationships_deleted": counters.relationships_deleted,
                "properties_set": counters.properties_set
            }

        with self._driver.session() as session:
            return session.execute_write(write_tx)

    async def execute_read_async(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """异步执行读事务

        使用ThreadPoolExecutor包装同步操作，避免阻塞事件循环。

        Args:
            query: Cypher查询语句
            parameters: 查询参数字典

        Returns:
            List[Dict]: 查询结果列表

        Raises:
            RuntimeError: 驱动未初始化
        """
        if not self.is_initialized():
            raise RuntimeError("Neo4j driver not initialized")

        loop = asyncio.get_event_loop()

        def _execute():
            return self.execute_read(query, parameters)

        return await loop.run_in_executor(self._executor, _execute)

    async def execute_write_async(self, query: str, parameters: Optional[Dict] = None) -> Dict:
        """异步执行写事务

        使用ThreadPoolExecutor包装同步操作，避免阻塞事件循环。

        Args:
            query: Cypher查询语句
            parameters: 查询参数字典

        Returns:
            Dict: 统计信息

        Raises:
            RuntimeError: 驱动未初始化
        """
        if not self.is_initialized():
            raise RuntimeError("Neo4j driver not initialized")

        loop = asyncio.get_event_loop()

        def _execute():
            return self.execute_write(query, parameters)

        return await loop.run_in_executor(self._executor, _execute)
