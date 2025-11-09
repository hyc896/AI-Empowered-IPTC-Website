# -*- coding: utf-8 -*-

"""
简化版采集器服务
不启动实际的采集器，只提供服务框架
"""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class SimpleCollectorService:
    """简化版采集器服务"""

    def __init__(self):
        """初始化采集器服务"""
        self._running = False
        self._startup_time = None

    async def start(self):
        """启动采集器服务（简化版本）"""
        if self._running:
            logger.warning("【采集器服务】已在运行中")
            return

        self._running = True
        self._startup_time = datetime.now()
        logger.info("=== 启动简化版消息采集器服务 ===")
        logger.info("【采集器服务】简化版本，不启动实际采集器")

    async def stop(self):
        """停止采集器服务"""
        if not self._running:
            return

        logger.info("【采集器服务】正在停止采集器服务...")
        self._running = False
        logger.info("【采集器服务】采集器服务已停止")

    def is_running(self) -> bool:
        """检查服务是否运行中"""
        return self._running

    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        uptime = None
        if self._startup_time:
            uptime = (datetime.now() - self._startup_time).total_seconds()

        return {
            "running": self._running,
            "collectors": [],  # 简化版本无采集器
            "collector_count": 0,
            "startup_time": self._startup_time,
            "uptime_seconds": uptime,
            "stats": {}
        }

    async def trigger_manual_collect(self, source_name: str) -> bool:
        """手动触发采集（简化版本不支持）"""
        logger.warning(f"【采集器服务】简化版本不支持手动触发: {source_name}")
        return False

    async def restart_collector(self, source_name: str) -> bool:
        """重启采集器（简化版本不支持）"""
        logger.warning(f"【采集器服务】简化版本不支持重启采集器: {source_name}")
        return False

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "running" if self._running else "stopped",
            "collectors": [],
            "healthy_collectors": 0,
            "total_collectors": 0,
            "startup_time": self._startup_time,
            "note": "简化版本，无实际采集器"
        }


# 创建全局实例
collector_service = SimpleCollectorService()