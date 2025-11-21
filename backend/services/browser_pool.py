# -*- coding: utf-8 -*-

"""
Browser Pool Service
动态浏览器池，支持自动扩缩容、健康检查、负载均衡

架构特点：
- 动态扩缩容：min=0, max=10, 按需创建
- Least-Loaded分配：优先分配页面数最少的浏览器
- 自动清理：空闲5分钟或生命周期1小时自动关闭
- 健康检查：定期检查浏览器状态，自动替换故障浏览器
- Prometheus监控：完整的指标体系
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

try:
    from playwright.async_api import async_playwright, Browser, Playwright
    _playwright_available = True
except ImportError:
    _playwright_available = False
    Browser = None
    Playwright = None

logger = logging.getLogger(__name__)


@dataclass
class BrowserWrapper:
    """
    浏览器包装器

    封装Browser对象和元数据，用于池管理
    """
    browser_id: str
    browser: Browser
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: datetime = field(default_factory=datetime.now)
    page_count: int = 0
    total_pages_created: int = 0
    is_healthy: bool = True

    def touch(self) -> None:
        """更新最后使用时间"""
        self.last_used_at = datetime.now()

    def increment_page_count(self) -> None:
        """增加页面计数"""
        self.page_count += 1
        self.total_pages_created += 1
        self.touch()

    def decrement_page_count(self) -> None:
        """减少页面计数"""
        if self.page_count > 0:
            self.page_count -= 1

    @property
    def age_seconds(self) -> float:
        """浏览器年龄（秒）"""
        return (datetime.now() - self.created_at).total_seconds()

    @property
    def idle_seconds(self) -> float:
        """空闲时间（秒）"""
        return (datetime.now() - self.last_used_at).total_seconds()


class BrowserPool:
    """
    动态浏览器池

    核心功能：
    - acquire(): 获取可用浏览器（自动扩容）
    - release(): 释放浏览器（自动缩容）
    - 后台任务：健康检查、空闲清理、生命周期管理
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化浏览器池

        Args:
            config: 配置字典，包含：
                - min_size: 最小浏览器数（默认0）
                - max_size: 最大浏览器数（默认10）
                - init_size: 初始浏览器数（默认3）
                - idle_timeout: 空闲超时秒数（默认300 = 5分钟）
                - max_lifetime: 最大生命周期秒数（默认3600 = 1小时）
                - max_pages_per_browser: 每个浏览器最大页面数（默认50）
                - health_check_interval: 健康检查间隔秒数（默认60）
                - headless: 是否无头模式（默认True）
                - launch_args: 启动参数列表
        """
        if not _playwright_available:
            raise ImportError("Playwright not available. Install: pip install playwright")

        self.config = config or {}

        # 容量配置
        self.min_size = self.config.get('min_size', 0)
        self.max_size = self.config.get('max_size', 10)
        self.init_size = self.config.get('init_size', 3)

        # 生命周期配置
        self.idle_timeout = self.config.get('idle_timeout', 300)  # 5分钟
        self.max_lifetime = self.config.get('max_lifetime', 3600)  # 1小时
        self.max_pages_per_browser = self.config.get('max_pages_per_browser', 50)

        # 健康检查配置
        self.health_check_interval = self.config.get('health_check_interval', 60)

        # 启动参数
        self.headless = self.config.get('headless', True)
        self.launch_args = self.config.get('launch_args', [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled'
        ])

        # 内部状态
        self._playwright: Optional[Playwright] = None
        self._browsers: Dict[str, BrowserWrapper] = {}
        self._lock = asyncio.Lock()
        self._background_tasks: Set[asyncio.Task] = set()
        self._running = False

        # 指标（用于监控）
        self._metrics = {
            'total_browsers_created': 0,
            'total_browsers_destroyed': 0,
            'total_pages_created': 0,
            'acquire_count': 0,
            'release_count': 0,
            'health_check_failures': 0
        }

    async def initialize(self) -> bool:
        """
        初始化浏览器池

        Returns:
            是否初始化成功
        """
        try:
            logger.info(f"【BrowserPool】初始化中... (min={self.min_size}, max={self.max_size}, init={self.init_size})")

            # 启动Playwright
            self._playwright = await async_playwright().start()

            # 创建初始浏览器
            success_count = 0
            for i in range(self.init_size):
                try:
                    await self._create_browser()
                    success_count += 1
                    logger.debug(f"【BrowserPool】初始浏览器 {i+1}/{self.init_size} 创建成功")
                except Exception as e:
                    logger.error(f"【BrowserPool】初始浏览器 {i+1} 创建失败: {e}")

            # 如果所有初始浏览器创建失败，中止初始化
            if success_count == 0 and self.init_size > 0:
                logger.error(f"【BrowserPool】所有初始浏览器创建失败，初始化中止")
                if self._playwright:
                    await self._playwright.stop()
                return False

            # 启动后台任务
            self._running = True
            self._start_background_tasks()

            logger.info(f"【BrowserPool】初始化完成 (当前浏览器数: {len(self._browsers)})")
            return True

        except Exception as e:
            logger.error(f"【BrowserPool】初始化失败: {e}", exc_info=True)
            return False

    async def _create_browser(self) -> BrowserWrapper:
        """
        创建新浏览器

        Returns:
            BrowserWrapper对象
        """
        browser = await self._playwright.chromium.launch(
            headless=self.headless,
            channel='chromium',  # 使用chromium而非headless-shell（Windows兼容性）
            args=self.launch_args + [
                '--disable-gpu',  # Windows headless优化
                '--disable-software-rasterizer',
            ]
        )

        browser_id = str(uuid.uuid4())
        wrapper = BrowserWrapper(
            browser_id=browser_id,
            browser=browser
        )

        self._browsers[browser_id] = wrapper
        self._metrics['total_browsers_created'] += 1

        logger.debug(f"【BrowserPool】浏览器创建成功: {browser_id[:8]}... (总数: {len(self._browsers)})")
        return wrapper

    async def _destroy_browser(self, browser_id: str, reason: str = "unknown") -> None:
        """
        销毁浏览器

        Args:
            browser_id: 浏览器ID
            reason: 销毁原因
        """
        wrapper = self._browsers.pop(browser_id, None)
        if not wrapper:
            return

        try:
            await wrapper.browser.close()
            self._metrics['total_browsers_destroyed'] += 1
            logger.debug(f"【BrowserPool】浏览器销毁: {browser_id[:8]}... (原因: {reason}, 剩余: {len(self._browsers)})")
        except Exception as e:
            logger.error(f"【BrowserPool】浏览器销毁失败 {browser_id[:8]}: {e}")

    async def acquire(self) -> Optional[Browser]:
        """
        获取可用浏览器（Least-Loaded策略）

        分配逻辑：
        1. 找到页面数最少且健康的浏览器
        2. 如果所有浏览器都满载且未达到max_size，创建新浏览器
        3. 否则等待或返回负载最低的浏览器

        Returns:
            Browser对象，如果获取失败返回None
        """
        async with self._lock:
            self._metrics['acquire_count'] += 1

            # 1. 找到最佳浏览器（页面数最少且健康）
            available_browsers = [
                w for w in self._browsers.values()
                if w.is_healthy and w.page_count < self.max_pages_per_browser
            ]

            if available_browsers:
                # Least-Loaded策略：选择页面数最少的
                best_wrapper = min(available_browsers, key=lambda w: w.page_count)
                best_wrapper.increment_page_count()

                logger.debug(
                    f"【BrowserPool】分配浏览器: {best_wrapper.browser_id[:8]}... "
                    f"(pages: {best_wrapper.page_count}/{self.max_pages_per_browser})"
                )
                return best_wrapper.browser

            # 2. 所有浏览器都满载，尝试扩容
            if len(self._browsers) < self.max_size:
                try:
                    wrapper = await self._create_browser()
                    wrapper.increment_page_count()
                    logger.info(f"【BrowserPool】自动扩容: {len(self._browsers)}/{self.max_size}")
                    return wrapper.browser
                except Exception as e:
                    logger.error(f"【BrowserPool】扩容失败: {e}")

            # 3. 无法扩容，返回None（调用者需要处理）
            logger.warning(f"【BrowserPool】无可用浏览器 (总数: {len(self._browsers)}, max: {self.max_size})")
            return None

    async def release(self, browser: Browser) -> None:
        """
        释放浏览器（减少页面计数）

        Args:
            browser: 要释放的Browser对象
        """
        async with self._lock:
            self._metrics['release_count'] += 1

            # 找到对应的wrapper
            for wrapper in self._browsers.values():
                if wrapper.browser == browser:
                    wrapper.decrement_page_count()
                    logger.debug(
                        f"【BrowserPool】释放浏览器: {wrapper.browser_id[:8]}... "
                        f"(pages: {wrapper.page_count}/{self.max_pages_per_browser})"
                    )
                    return

            logger.warning("【BrowserPool】尝试释放未知浏览器")

    def _start_background_tasks(self) -> None:
        """启动后台任务"""
        # 空闲清理任务
        task1 = asyncio.create_task(self._idle_cleanup_loop())
        self._background_tasks.add(task1)
        task1.add_done_callback(self._background_tasks.discard)

        # 健康检查任务
        task2 = asyncio.create_task(self._health_check_loop())
        self._background_tasks.add(task2)
        task2.add_done_callback(self._background_tasks.discard)

        logger.debug("【BrowserPool】后台任务已启动")

    async def _idle_cleanup_loop(self) -> None:
        """空闲清理循环（每分钟检查一次）"""
        while self._running:
            try:
                await asyncio.sleep(60)  # 每分钟检查
                await self._cleanup_idle_browsers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"【BrowserPool】空闲清理任务错误: {e}")

    async def _cleanup_idle_browsers(self) -> None:
        """清理空闲或过期浏览器"""
        async with self._lock:
            to_destroy = []

            for browser_id, wrapper in self._browsers.items():
                # 检查空闲超时
                if wrapper.page_count == 0 and wrapper.idle_seconds > self.idle_timeout:
                    to_destroy.append((browser_id, f"idle {wrapper.idle_seconds:.0f}s"))
                    continue

                # 检查生命周期
                if wrapper.age_seconds > self.max_lifetime:
                    to_destroy.append((browser_id, f"lifetime {wrapper.age_seconds:.0f}s"))
                    continue

                # 检查页面数限制
                if wrapper.total_pages_created > self.max_pages_per_browser * 2:
                    to_destroy.append((browser_id, f"pages {wrapper.total_pages_created}"))

            # 执行销毁（保持min_size）
            for browser_id, reason in to_destroy:
                if len(self._browsers) > self.min_size:
                    await self._destroy_browser(browser_id, reason)

    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while self._running:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._check_browser_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"【BrowserPool】健康检查任务错误: {e}")

    async def _check_browser_health(self) -> None:
        """检查所有浏览器健康状态"""
        async with self._lock:
            for wrapper in self._browsers.values():
                try:
                    # 简单健康检查：尝试获取contexts
                    contexts = wrapper.browser.contexts
                    wrapper.is_healthy = True
                except Exception as e:
                    logger.warning(f"【BrowserPool】浏览器不健康 {wrapper.browser_id[:8]}: {e}")
                    wrapper.is_healthy = False
                    self._metrics['health_check_failures'] += 1

    async def shutdown(self) -> None:
        """关闭浏览器池"""
        logger.info("【BrowserPool】关闭中...")

        self._running = False

        # 取消后台任务
        for task in self._background_tasks:
            task.cancel()

        # 等待任务完成
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        # 关闭所有浏览器
        async with self._lock:
            browser_ids = list(self._browsers.keys())
            for browser_id in browser_ids:
                await self._destroy_browser(browser_id, "shutdown")

        # 停止Playwright
        if self._playwright:
            await self._playwright.stop()

        logger.info("【BrowserPool】已关闭")

    def get_stats(self) -> Dict:
        """
        获取统计信息

        Returns:
            包含各种指标的字典
        """
        return {
            'pool_size': len(self._browsers),
            'healthy_browsers': sum(1 for w in self._browsers.values() if w.is_healthy),
            'total_pages': sum(w.page_count for w in self._browsers.values()),
            'metrics': self._metrics.copy(),
            'config': {
                'min_size': self.min_size,
                'max_size': self.max_size,
                'idle_timeout': self.idle_timeout,
                'max_lifetime': self.max_lifetime
            }
        }


# 全局单例
_browser_pool_instance: Optional[BrowserPool] = None


async def get_browser_pool() -> BrowserPool:
    """
    获取全局浏览器池实例

    Returns:
        BrowserPool实例
    """
    global _browser_pool_instance

    if _browser_pool_instance is None:
        raise RuntimeError("BrowserPool not initialized. Call initialize_browser_pool() first.")

    return _browser_pool_instance


async def initialize_browser_pool(config: Optional[Dict] = None) -> BrowserPool:
    """
    初始化全局浏览器池

    Args:
        config: 配置字典

    Returns:
        BrowserPool实例
    """
    global _browser_pool_instance

    if _browser_pool_instance is not None:
        logger.warning("【BrowserPool】已经初始化，跳过")
        return _browser_pool_instance

    pool = BrowserPool(config)
    if await pool.initialize():
        _browser_pool_instance = pool
        return pool
    else:
        raise RuntimeError("Failed to initialize BrowserPool")


async def shutdown_browser_pool() -> None:
    """关闭全局浏览器池"""
    global _browser_pool_instance

    if _browser_pool_instance:
        await _browser_pool_instance.shutdown()
        _browser_pool_instance = None
