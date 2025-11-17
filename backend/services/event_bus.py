# -*- coding: utf-8 -*-
"""
EventBus事件总线

功能：
1. 基于asyncio.Queue的内存级pub/sub机制
2. 支持多订阅者广播
3. 自动清理死亡队列
4. 用于字段增强器→SSE推送的事件传递
"""

import asyncio
import logging
from typing import Dict, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class EventType:
    """事件类型常量"""
    NEW_AI_MESSAGE = "new_ai_message"  # 新增AI消息
    MESSAGE_UPDATED = "message_updated"  # 消息更新
    REPORT_GENERATED = "report_generated"  # 日报生成完成


class EventBus:
    """
    全局事件总线（内存级，基于asyncio.Queue）

    设计特点：
    - 非阻塞发布：队列满时跳过该订阅者
    - 自动清理：死亡队列自动移除
    - 线程安全：使用asyncio.Lock保护订阅者列表
    """

    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def publish(self, event_type: str, data: dict):
        """
        发布事件

        Args:
            event_type: 事件类型（如"new_ai_message"）
            data: 事件数据（字典）
        """
        async with self._lock:
            if event_type not in self._subscribers:
                logger.debug(f"事件 {event_type} 无订阅者，跳过发布")
                return

            # 向所有订阅者推送
            dead_queues = []
            subscriber_count = len(self._subscribers[event_type])

            for queue in self._subscribers[event_type]:
                try:
                    # 非阻塞放入队列
                    queue.put_nowait(data)
                except asyncio.QueueFull:
                    # 队列满，标记为死亡（客户端可能已断开或处理过慢）
                    logger.warning(f"订阅者队列已满，标记为死亡队列")
                    dead_queues.append(queue)
                except Exception as e:
                    logger.error(f"发布事件失败: {e}", exc_info=True)
                    dead_queues.append(queue)

            # 清理死亡队列
            for queue in dead_queues:
                try:
                    self._subscribers[event_type].remove(queue)
                except ValueError:
                    pass

            if dead_queues:
                logger.info(f"清理 {len(dead_queues)} 个死亡队列，剩余 {len(self._subscribers[event_type])} 个订阅者")

            logger.debug(f"事件已发布: {event_type}，推送至 {subscriber_count - len(dead_queues)} 个订阅者")

    async def subscribe(self, event_type: str, maxsize: int = 100) -> asyncio.Queue:
        """
        订阅事件

        Args:
            event_type: 事件类型
            maxsize: 队列最大长度（防止内存溢出）

        Returns:
            订阅者队列
        """
        queue = asyncio.Queue(maxsize=maxsize)
        async with self._lock:
            self._subscribers[event_type].append(queue)
        logger.debug(f"新增订阅者: {event_type}，当前 {len(self._subscribers[event_type])} 个订阅者")
        return queue

    async def unsubscribe(self, event_type: str, queue: asyncio.Queue):
        """取消订阅"""
        async with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(queue)
                    logger.debug(f"取消订阅: {event_type}，剩余 {len(self._subscribers[event_type])} 个订阅者")
                except ValueError:
                    logger.warning(f"尝试取消不存在的订阅者")

    def get_subscriber_count(self, event_type: str) -> int:
        """获取订阅者数量（用于监控）"""
        return len(self._subscribers.get(event_type, []))

    def get_all_stats(self) -> Dict[str, int]:
        """获取所有事件类型的订阅者统计"""
        return {
            event_type: len(queues)
            for event_type, queues in self._subscribers.items()
        }


# 全局单例
_event_bus = None


def get_event_bus() -> EventBus:
    """获取全局EventBus实例"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        logger.info("EventBus全局实例已创建")
    return _event_bus
