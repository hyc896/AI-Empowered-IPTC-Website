# -*- coding: utf-8 -*-

"""
Redis缓存服务
提供统一的缓存接口，减少数据库查询压力
"""

import json
import logging
from typing import Optional, Any, List, Dict
from datetime import datetime, timedelta

import redis

logger = logging.getLogger(__name__)


class CacheService:
    """Redis缓存服务"""

    # 缓存Key前缀
    PREFIX = "mp:"

    # 缓存过期时间（秒）
    TTL_SHORT = 60          # 1分钟
    TTL_MEDIUM = 300        # 5分钟
    TTL_LONG = 3600         # 1小时
    TTL_STATS = 180         # 3分钟（统计数据）
    TTL_SOURCES = 600       # 10分钟（消息源列表）
    TTL_MESSAGES = 120      # 2分钟（消息列表）

    def __init__(self):
        """初始化Redis连接"""
        self._client: Optional[redis.Redis] = None
        self._connected = False

    def _get_client(self) -> Optional[redis.Redis]:
        """获取Redis客户端（延迟初始化）"""
        if self._client is not None:
            return self._client if self._connected else None

        try:
            from backend.config import ConfigManager

            config_manager = ConfigManager()
            if not config_manager.load_config('config.yaml'):
                logger.warning("【缓存服务】无法加载配置，缓存功能禁用")
                return None

            config = config_manager.get_config()
            redis_config = config.get('database', {}).get('redis', {})

            host = redis_config.get('host', 'localhost')
            port = redis_config.get('port', 6379)
            password = redis_config.get('password', '')
            db = redis_config.get('db', 0)

            self._client = redis.Redis(
                host=host,
                port=port,
                password=password if password else None,
                db=db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )

            # 测试连接
            self._client.ping()
            self._connected = True
            logger.info(f"【缓存服务】Redis连接成功: {host}:{port}/{db}")

            return self._client

        except Exception as e:
            logger.warning(f"【缓存服务】Redis连接失败，缓存功能禁用: {e}")
            self._connected = False
            return None

    def _make_key(self, *parts: str) -> str:
        """生成缓存Key"""
        return f"{self.PREFIX}{':'.join(str(p) for p in parts)}"

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        client = self._get_client()
        if not client:
            return None

        try:
            value = client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"【缓存服务】获取缓存失败 {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = TTL_MEDIUM) -> bool:
        """设置缓存"""
        client = self._get_client()
        if not client:
            return False

        try:
            client.setex(key, ttl, json.dumps(value, default=str, ensure_ascii=False))
            return True
        except Exception as e:
            logger.warning(f"【缓存服务】设置缓存失败 {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存"""
        client = self._get_client()
        if not client:
            return False

        try:
            client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"【缓存服务】删除缓存失败 {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的所有缓存"""
        client = self._get_client()
        if not client:
            return 0

        try:
            keys = list(client.scan_iter(match=pattern))
            if keys:
                return client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"【缓存服务】删除模式缓存失败 {pattern}: {e}")
            return 0

    # ========================
    # 业务缓存方法
    # ========================

    def get_stats(self) -> Optional[Dict[str, Any]]:
        """获取统计信息缓存"""
        key = self._make_key("stats", "overview")
        return self.get(key)

    def set_stats(self, stats: Dict[str, Any]) -> bool:
        """设置统计信息缓存"""
        key = self._make_key("stats", "overview")
        return self.set(key, stats, self.TTL_STATS)

    def get_sources(self, category: Optional[str] = None, is_active: Optional[bool] = None) -> Optional[List[Dict]]:
        """获取消息源列表缓存"""
        key = self._make_key("sources", category or "all", str(is_active))
        return self.get(key)

    def set_sources(self, sources: List[Dict], category: Optional[str] = None, is_active: Optional[bool] = None) -> bool:
        """设置消息源列表缓存"""
        key = self._make_key("sources", category or "all", str(is_active))
        return self.set(key, sources, self.TTL_SOURCES)

    def invalidate_sources(self) -> int:
        """使消息源缓存失效"""
        pattern = self._make_key("sources", "*")
        return self.delete_pattern(pattern)

    def get_messages(
        self,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        query: str = "",
        limit: int = 20,
        offset: int = 0,
        hours: int = 0
    ) -> Optional[tuple]:
        """获取消息列表缓存"""
        # 对于有搜索关键词的请求，不使用缓存
        if query and query.strip():
            return None

        key = self._make_key(
            "messages",
            source_type or "all",
            source_id or "all",
            f"l{limit}",
            f"o{offset}",
            f"h{hours}"
        )
        data = self.get(key)
        if data and isinstance(data, dict):
            return data.get('results'), data.get('total')
        return None

    def set_messages(
        self,
        results: List[Dict],
        total: int,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        query: str = "",
        limit: int = 20,
        offset: int = 0,
        hours: int = 0
    ) -> bool:
        """设置消息列表缓存"""
        # 对于有搜索关键词的请求，不缓存
        if query and query.strip():
            return False

        key = self._make_key(
            "messages",
            source_type or "all",
            source_id or "all",
            f"l{limit}",
            f"o{offset}",
            f"h{hours}"
        )
        return self.set(key, {'results': results, 'total': total}, self.TTL_MESSAGES)

    def invalidate_messages(self, source_type: Optional[str] = None) -> int:
        """使消息缓存失效"""
        if source_type:
            pattern = self._make_key("messages", source_type, "*")
        else:
            pattern = self._make_key("messages", "*")
        return self.delete_pattern(pattern)

    def get_monitor_status(self) -> Optional[Dict[str, Any]]:
        """获取监控状态缓存"""
        key = self._make_key("monitor", "system")
        return self.get(key)

    def set_monitor_status(self, status: Dict[str, Any]) -> bool:
        """设置监控状态缓存"""
        key = self._make_key("monitor", "system")
        return self.set(key, status, self.TTL_SHORT)

    def get_queue_status(self) -> Optional[Dict[str, Any]]:
        """获取队列状态缓存"""
        key = self._make_key("monitor", "queues")
        return self.get(key)

    def set_queue_status(self, status: Dict[str, Any]) -> bool:
        """设置队列状态缓存"""
        key = self._make_key("monitor", "queues")
        return self.set(key, status, self.TTL_SHORT)

    def is_connected(self) -> bool:
        """检查Redis是否连接"""
        client = self._get_client()
        if not client:
            return False
        try:
            client.ping()
            return True
        except:
            return False


# 全局缓存服务实例
cache_service = CacheService()
