# -*- coding: utf-8 -*-

"""
简化版消息检索服务
只支持MySQL关键词搜索，不依赖复杂的PersonalAgent模块
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import pymysql

logger = logging.getLogger(__name__)


class SimpleSearchService:
    """简化版消息检索服务"""

    def __init__(self):
        """初始化检索服务"""
        # 数据库配置
        self.db_config = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "123456",
            "database": "message_platform",
            "charset": "utf8mb4"
        }

        logger.info("【检索服务】简化版本初始化完成")

    async def search(
        self,
        source_type: Optional[str] = None,
        query: str = "",
        time_range: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        简化的关键词搜索

        Args:
            source_type: 消息源类型 (news, academic, tech)
            query: 搜索关键词
            time_range: 时间范围（暂未实现）
            limit: 返回结果数量
            **kwargs: 其他参数

        Returns:
            搜索结果列表
        """
        start_time = datetime.now()
        logger.info(f"【消息检索】开始搜索 - 类型: {source_type}, 关键词: '{query}', 限制: {limit}")

        if not query or not query.strip():
            logger.warning("【消息检索】查询关键词为空，返回空结果")
            return []

        try:
            # 根据source_type确定查询的表
            if source_type == "news":
                table_name = "mp_tonghuashun_messages"
            elif source_type == "tech":
                table_name = "mp_kr36_messages"
            elif source_type == "academic":
                table_name = "mp_arxiv_messages"
            else:
                # 默认查询同花顺
                table_name = "mp_tonghuashun_messages"

            # 执行数据库查询
            results = await self._search_mysql(table_name, query, limit)

            search_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"【消息检索】搜索完成 - 找到 {len(results)} 条结果，耗时 {search_time:.2f}s")

            return results

        except Exception as e:
            logger.error(f"【消息检索】搜索失败: {e}", exc_info=True)
            return []

    async def _search_mysql(self, table_name: str, query: str, limit: int) -> List[Dict[str, Any]]:
        """执行MySQL搜索"""
        connection = None
        try:
            # 建立数据库连接
            connection = pymysql.connect(**self.db_config)

            with connection.cursor() as cursor:
                # 构建SQL查询
                sql = f"""
                    SELECT title, content, provider, published_at, url
                    FROM {table_name}
                    WHERE title LIKE %s OR content LIKE %s
                    ORDER BY published_at DESC
                    LIMIT %s
                """

                search_pattern = f"%{query}%"
                cursor.execute(sql, (search_pattern, search_pattern, limit))

                # 获取查询结果
                rows = cursor.fetchall()

                # 格式化结果
                results = []
                for row in rows:
                    results.append({
                        "title": row[0] if row[0] else "",
                        "content": row[1] if row[1] else "",
                        "provider": row[2] if row[2] else "",
                        "published_at": row[3].isoformat() if row[3] else "",
                        "url": row[4] if row[4] else "",
                        "source_name": table_name.replace("mp_", "").replace("_messages", ""),
                        "source": "mysql"
                    })

                return results

        except Exception as e:
            logger.error(f"【MySQL搜索】查询失败: {e}")
            return []

        finally:
            if connection:
                connection.close()

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 测试数据库连接
            connection = pymysql.connect(**self.db_config)
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            connection.close()

            if result and result[0] == 1:
                return {
                    "status": "healthy",
                    "database": "connected",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "database": "error",
                    "error": "数据库查询测试失败"
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }


# 创建全局实例
search_service = SimpleSearchService()