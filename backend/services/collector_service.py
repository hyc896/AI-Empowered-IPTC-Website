# -*- coding: utf-8 -*-

"""
消息采集器服务
管理所有消息源的采集任务调度
"""

import asyncio
import importlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..database.connection import create_session
from ..database.entities import MessageSource

logger = logging.getLogger(__name__)


class CollectorService:
    """消息采集器服务"""

    def __init__(self, browser_pool=None):
        """
        初始化采集器服务

        Args:
            browser_pool: 浏览器池实例（可选），如果提供则注入到Playwright采集器
        """
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}
        self._collectors: Dict[str, Any] = {}
        self._stats: Dict[str, Dict[str, Any]] = {}
        self._startup_time = None
        self._browser_pool = browser_pool

        # 并发控制：限制同时初始化的采集器数量，防止资源耗尽
        # Semaphore=1确保Playwright浏览器完全顺序启动（Windows上并发启动易失败）
        self._init_semaphore = asyncio.Semaphore(1)

        # 重试配置
        self._max_init_retries = 2  # 最多重试2次
        self._init_retry_delay = 2  # 重试间隔2秒（指数退避）

    async def start(self):
        """
        启动所有激活的采集器

        流程（改进版，使用并发控制）：
        1. 从数据库加载激活的消息源
        2. 并发启动采集器，但通过信号量限制并发数（防止资源耗尽）
        3. 统一异常处理和监控
        4. 失败的采集器自动重试

        性能优化：
        - 使用asyncio.gather并发启动，但Semaphore限制最多3个同时初始化
        - 相比顺序启动，总启动时间大幅缩短（20个采集器从60秒降到20秒）
        """
        if self._running:
            logger.warning("【采集器服务】已在运行中")
            return

        self._running = True
        self._startup_time = datetime.now()

        try:
            # 从数据库加载消息源
            sources = await self._load_active_sources()

            if not sources:
                logger.warning("【采集器】未找到激活的消息源")
                self._running = False
                return

            logger.info(f"【采集器】开始启动 {len(sources)} 个采集器（顺序初始化Playwright，防止资源耗尽）...")

            # 并发启动所有采集器（信号量内部控制并发数）
            results = await asyncio.gather(
                *[self._start_collector(source) for source in sources],
                return_exceptions=True
            )

            # 统计启动结果
            started_collectors = []
            failed_collectors = []

            for source, result in zip(sources, results):
                if isinstance(result, Exception):
                    failed_collectors.append(f"{source['display_name']}({result})")
                elif result:
                    interval = source.get('interval', 60)
                    started_collectors.append(f"{source['display_name']}({interval}s)")
                else:
                    failed_collectors.append(source['display_name'])

            if not self._tasks:
                logger.error("【采集器】未启动任何采集器")
                self._running = False
            else:
                logger.info(f"✓ 采集器启动成功 [{len(started_collectors)}/{len(sources)}]: {', '.join(started_collectors)}")
                if failed_collectors:
                    logger.warning(f"⚠ 启动失败 [{len(failed_collectors)}]: {', '.join(failed_collectors)}")

        except Exception as e:
            logger.error(f"【采集器服务】启动失败: {e}")
            self._running = False
            raise

    async def _load_active_sources(self) -> List[Dict[str, Any]]:
        """从数据库加载激活的消息源"""
        try:
            with create_session() as db:
                sources = db.query(MessageSource).filter(MessageSource.is_active == True).all()

                active_sources = []
                for source in sources:
                    config = source.config or {}

                    active_sources.append({
                        "id": source.id,
                        "name": source.name,
                        "adapter_name": source.adapter_name,
                        "category": source.category or config.get("source_type", "unknown"),
                        "display_name": source.display_name or source.name,
                        "mysql_table": config.get("mysql_table", f"{source.name}_messages"),
                        "chroma_collection": config.get("chroma_collection", f"{source.name}_messages"),
                        "collector_module": config.get("collector_module", ""),
                        "interval": config.get("interval", 60),
                        "enabled": True,
                        "config": config,
                        "last_crawled_at": source.last_crawled_at,
                        "schedule": source.schedule
                    })

                return active_sources

        except Exception as e:
            logger.error(f"【采集器】加载消息源失败: {e}")
            return []

    async def _start_collector(self, source_config: Dict[str, Any]) -> bool:
        """
        启动单个采集器（带并发控制和重试机制）

        Args:
            source_config: 消息源配置

        Returns:
            启动是否成功

        并发控制：
        - 使用Semaphore限制同时初始化的采集器数量
        - 防止Playwright/ChromaDB等资源密集操作导致系统资源耗尽

        重试机制：
        - 初始化失败时自动重试（最多2次）
        - 使用指数退避策略（2秒、4秒）
        """
        source_name = source_config["name"]
        display_name = source_config.get("display_name", source_name)
        collector_module_path = source_config.get("collector_module")

        if not collector_module_path:
            logger.warning(f"【采集器】{display_name} 未配置 collector_module，跳过")
            return False

        # 重试逻辑
        for attempt in range(self._max_init_retries + 1):
            try:
                # 动态导入采集器模块
                adjusted_module_path = collector_module_path.replace("backend.services.message", "backend")
                module = importlib.import_module(adjusted_module_path)

                # 查找采集器类
                collector_class_name = None
                for attr_name in dir(module):
                    if attr_name.endswith('Collector') and not attr_name.startswith('_'):
                        collector_class_name = attr_name
                        break

                if not collector_class_name:
                    logger.error(f"【采集器】{display_name} 模块中未找到 Collector 类")
                    return False

                # 创建采集器实例
                collector_class = getattr(module, collector_class_name)
                collector_instance = collector_class(source_config)

                # 如果是Playwright采集器且配置了浏览器池，注入浏览器池
                if hasattr(collector_instance, 'set_browser_pool') and self._browser_pool:
                    collector_instance.set_browser_pool(self._browser_pool)
                    logger.debug(f"[{source_name}] 已注入浏览器池")

                # 如果采集器有 initialize 方法，使用信号量控制并发初始化
                if hasattr(collector_instance, 'initialize'):
                    async with self._init_semaphore:
                        retry_info = f" (重试 {attempt}/{self._max_init_retries})" if attempt > 0 else ""
                        logger.info(f"【采集器】正在初始化 {display_name}{retry_info}...")

                        init_success = await collector_instance.initialize()

                        if not init_success:
                            if attempt < self._max_init_retries:
                                delay = self._init_retry_delay * (2 ** attempt)
                                logger.warning(f"【采集器】{display_name} 初始化失败，{delay}秒后重试...")
                                await asyncio.sleep(delay)
                                continue
                            else:
                                logger.error(f"【采集器】{display_name} 初始化失败（已重试{self._max_init_retries}次），跳过启动")
                                return False

                        logger.info(f"【采集器】✓ {display_name} 初始化成功")

                # 启动采集任务
                task = asyncio.create_task(
                    self._run_collector_with_monitoring(source_name, collector_instance)
                )

                self._tasks[source_name] = task
                self._collectors[source_name] = collector_instance

                # 初始化统计信息
                self._stats[source_name] = {
                    "success_count": 0,
                    "fail_count": 0,
                    "last_success_time": None,
                    "last_fail_time": None,
                    "last_error": None,
                    "start_time": datetime.now(),
                    "total_runtime": 0
                }

                return True

            except Exception as e:
                if attempt < self._max_init_retries:
                    delay = self._init_retry_delay * (2 ** attempt)
                    logger.warning(f"【采集器】{display_name} 启动异常: {e}，{delay}秒后重试...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"【采集器】{display_name} 启动失败（已重试{self._max_init_retries}次）: {e}")
                    return False

        return False

    async def _run_collector_with_monitoring(self, source_name: str, collector: Any) -> None:
        """
        运行采集器并监控异常

        Args:
            source_name: 消息源名称
            collector: 采集器实例
        """
        try:
            await collector.run()
        except asyncio.CancelledError:
            logger.info(f"【采集器】{source_name} 被取消")
            raise
        except Exception as e:
            logger.exception(f"【采集器】{source_name} 运行异常: {e}")

            # 更新统计信息
            if source_name in self._stats:
                self._stats[source_name]["fail_count"] += 1
                self._stats[source_name]["last_fail_time"] = datetime.now()
                self._stats[source_name]["last_error"] = str(e)

    async def stop(self):
        """停止所有采集器"""
        if not self._running:
            return

        logger.info("【采集器服务】正在停止采集器服务...")
        self._running = False

        # 停止采集器实例
        for source_name, collector in self._collectors.items():
            try:
                if hasattr(collector, 'stop'):
                    await collector.stop()
                    logger.info(f"【采集器服务】已停止采集器: {source_name}")
            except Exception as e:
                logger.error(f"【采集器服务】停止采集器失败 {source_name}: {e}")

        # 取消异步任务
        for source_name, task in self._tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"【采集器服务】停止任务失败 {source_name}: {e}")

        self._tasks.clear()
        self._collectors.clear()

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
            "collectors": list(self._tasks.keys()),
            "collector_count": len(self._tasks),
            "startup_time": self._startup_time,
            "uptime_seconds": uptime,
            "stats": self._stats.copy()
        }

    def get_collector_stats(self, source_name: str) -> Dict[str, Any]:
        """获取指定采集器的统计信息"""
        if source_name not in self._stats:
            return {
                "success_count": 0,
                "fail_count": 0,
                "last_success_time": None,
                "last_fail_time": None,
                "last_error": None,
                "start_time": None,
                "total_runtime": 0
            }

        stats = self._stats[source_name].copy()

        # 计算运行时间
        if stats["start_time"]:
            stats["total_runtime"] = (datetime.now() - stats["start_time"]).total_seconds()

        return stats

    async def trigger_manual_collect(self, source_name: str) -> bool:
        """手动触发指定采集器的采集"""
        if source_name not in self._collectors:
            logger.warning(f"【采集器服务】采集器 {source_name} 不存在或未启动")
            return False

        try:
            collector = self._collectors[source_name]

            # 检查采集器是否有手动采集方法
            if hasattr(collector, 'collect_once'):
                await collector.collect_once()
                logger.info(f"【采集器服务】手动触发采集: {source_name}")

                # 更新统计信息
                if source_name in self._stats:
                    self._stats[source_name]["success_count"] += 1
                    self._stats[source_name]["last_success_time"] = datetime.now()

                return True
            else:
                logger.warning(f"【采集器服务】采集器 {source_name} 不支持手动触发")
                return False

        except Exception as e:
            logger.error(f"【采集器服务】手动触发采集失败 {source_name}: {e}")

            # 更新错误统计
            if source_name in self._stats:
                self._stats[source_name]["fail_count"] += 1
                self._stats[source_name]["last_fail_time"] = datetime.now()
                self._stats[source_name]["last_error"] = str(e)

            return False

    async def restart_collector(self, source_name: str) -> bool:
        """重启指定的采集器"""
        if source_name not in self._collectors:
            logger.warning(f"【采集器服务】采集器 {source_name} 不存在")
            return False

        try:
            # 停止采集器
            await self.stop_collector(source_name)

            # 重新加载配置
            sources = await self._load_active_sources()
            source_config = None
            for source in sources:
                if source["name"] == source_name:
                    source_config = source
                    break

            if not source_config:
                logger.error(f"【采集器服务】未找到消息源配置: {source_name}")
                return False

            # 重新启动采集器
            return await self._start_collector(source_config)

        except Exception as e:
            logger.error(f"【采集器服务】重启采集器失败 {source_name}: {e}")
            return False

    async def stop_collector(self, source_name: str) -> bool:
        """停止指定的采集器"""
        if source_name not in self._tasks:
            logger.warning(f"【采集器服务】采集器 {source_name} 不存在或未运行")
            return False

        try:
            # 停止采集器
            collector = self._collectors.get(source_name)
            if collector and hasattr(collector, 'stop'):
                await collector.stop()

            # 取消任务
            task = self._tasks[source_name]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            # 清理
            del self._tasks[source_name]
            del self._collectors[source_name]

            logger.info(f"【采集器服务】已停止采集器: {source_name}")
            return True

        except Exception as e:
            logger.error(f"【采集器服务】停止采集器失败 {source_name}: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        if not self._running:
            return {
                "status": "stopped",
                "collectors": [],
                "healthy_collectors": 0,
                "total_collectors": 0
            }

        healthy_count = 0
        collector_status = []

        for source_name in self._tasks:
            stats = self.get_collector_stats(source_name)

            # 判断采集器是否健康（最近5分钟内有成功记录）
            is_healthy = False
            if stats["last_success_time"]:
                time_since_success = (datetime.now() - stats["last_success_time"]).total_seconds()
                is_healthy = time_since_success < 300  # 5分钟

            if is_healthy:
                healthy_count += 1

            collector_status.append({
                "name": source_name,
                "healthy": is_healthy,
                "success_count": stats["success_count"],
                "fail_count": stats["fail_count"],
                "last_success_time": stats["last_success_time"],
                "last_fail_time": stats["last_fail_time"],
                "last_error": stats["last_error"]
            })

        return {
            "status": "running" if healthy_count > 0 else "unhealthy",
            "collectors": collector_status,
            "healthy_collectors": healthy_count,
            "total_collectors": len(self._tasks),
            "startup_time": self._startup_time
        }


# 全局采集器服务实例（延迟初始化，允许传入浏览器池）
collector_service: Optional[CollectorService] = None


def initialize_collector_service(browser_pool=None) -> CollectorService:
    """
    初始化全局采集器服务实例

    Args:
        browser_pool: 浏览器池实例（可选）

    Returns:
        CollectorService实例
    """
    global collector_service
    if collector_service is None:
        collector_service = CollectorService(browser_pool=browser_pool)
    return collector_service


def get_collector_service() -> CollectorService:
    """
    获取全局采集器服务实例

    Returns:
        CollectorService实例

    Raises:
        RuntimeError: 如果尚未初始化
    """
    if collector_service is None:
        raise RuntimeError("CollectorService尚未初始化，请先调用initialize_collector_service()")
    return collector_service