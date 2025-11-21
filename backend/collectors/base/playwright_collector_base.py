# -*- coding: utf-8 -*-

"""
Playwright采集器基类

提供统一的浏览器管理、资源清理和浏览器池集成功能。

使用方式：
    class MyCollector(PlaywrightCollectorBase):
        async def _collect_once(self):
            # 实现具体采集逻辑
            page = await self._browser.new_page()
            try:
                await page.goto('https://example.com')
                # ... 采集逻辑
            finally:
                await page.close()
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Playwright, Browser
import asyncio
import logging

logger = logging.getLogger(__name__)


class PlaywrightCollectorBase(ABC):
    """
    Playwright采集器基类

    功能：
    - 统一的浏览器初始化和关闭
    - 浏览器池集成支持（可选）
    - 资源管理和错误处理
    - 定时采集循环

    子类只需实现：
    - _collect_once(): 单次采集逻辑
    - _on_initialize() (可选): 额外初始化逻辑
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化基类

        Args:
            config: 采集器配置字典，必须包含：
                - interval: 采集间隔（秒）
                - id: 消息源ID
        """
        self.config = config
        self.interval = config.get('interval', 3600)
        self.source_id = config.get('id', 'auto')

        # 采集器名称（子类名去掉Collector后缀）
        self.collector_name = self.__class__.__name__.replace('Collector', '')

        # 浏览器实例
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._browser_pool = None  # 浏览器池（由CollectorService注入）
        self._running = False

        # 浏览器配置（子类可覆盖）
        self.browser_args: List[str] = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage'
        ]
        self.headless: bool = True

    async def initialize(self) -> bool:
        """
        初始化采集器（启动浏览器或从池中获取）

        Returns:
            是否初始化成功
        """
        try:
            # 如果配置了浏览器池，从池中获取浏览器
            if self._browser_pool:
                self._browser = await self._browser_pool.acquire()
                if not self._browser:
                    logger.error(f"【{self.collector_name}】无法从浏览器池获取浏览器")
                    return False
                logger.info(f"【{self.collector_name}】从浏览器池获取浏览器成功")
            else:
                # 传统方式：直接启动浏览器
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=self.headless,
                    channel='chromium',  # 使用chromium而非headless-shell（Windows兼容性）
                    args=self.browser_args + [
                        '--disable-gpu',  # Windows headless优化
                        '--disable-software-rasterizer',
                    ]
                )
                logger.info(f"【{self.collector_name}】浏览器启动成功（新headless模式）")

            # 调用子类的初始化钩子
            if not await self._on_initialize():
                return False

            logger.info(f"【{self.collector_name}】采集器初始化成功")
            return True
        except Exception as e:
            logger.error(f"【{self.collector_name}】采集器初始化失败: {e}")
            return False

    async def _on_initialize(self) -> bool:
        """
        子类初始化钩子（可选实现）

        用于子类执行额外的初始化逻辑，如：
        - 创建ChromaDB collection
        - 验证配置参数
        - 初始化数据库连接

        Returns:
            是否初始化成功
        """
        return True

    async def run(self) -> None:
        """
        主循环：定时采集

        执行流程：
        1. 检查浏览器是否初始化，未初始化则执行initialize()
        2. 进入定时循环
        3. 每隔interval秒执行一次_collect_once()
        4. 捕获异常，确保单次失败不影响后续采集
        """
        # 检查是否已由 CollectorService 初始化过
        if not self._browser:
            if not await self.initialize():
                logger.error(f"【{self.collector_name}】采集器初始化失败，退出")
                return

        self._running = True
        logger.info(f"【{self.collector_name}】采集器已启动 (采集间隔={self.interval}秒)")

        while self._running:
            try:
                await self._collect_once()
            except Exception as e:
                logger.error(f"【{self.collector_name}】采集失败: {e}", exc_info=True)

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """
        停止采集器

        执行流程：
        1. 设置_running=False，终止run()循环
        2. 调用_close_browser()清理浏览器资源
        """
        self._running = False
        await self._close_browser()
        logger.info(f"【{self.collector_name}】采集器已停止")

    async def _close_browser(self) -> None:
        """
        关闭浏览器

        根据初始化方式选择不同的清理策略：
        - 如果使用浏览器池：释放浏览器回池中
        - 如果独立启动：直接关闭浏览器和Playwright
        """
        try:
            # 如果使用浏览器池，释放回池中
            if self._browser_pool and self._browser:
                await self._browser_pool.release(self._browser)
                logger.debug(f"【{self.collector_name}】浏览器已释放回池")
            else:
                # 传统方式：直接关闭
                if self._browser:
                    await self._browser.close()
                if self._playwright:
                    await self._playwright.stop()
                logger.debug(f"【{self.collector_name}】浏览器已关闭")
        except Exception as e:
            logger.error(f"【{self.collector_name}】关闭浏览器失败: {e}")

    def set_browser_pool(self, browser_pool):
        """
        设置浏览器池（由CollectorService调用）

        启用浏览器池后：
        - initialize()时从池中acquire浏览器
        - stop()时release浏览器回池

        Args:
            browser_pool: 浏览器池实例（BrowserPool对象）
        """
        self._browser_pool = browser_pool
        logger.debug(f"【{self.collector_name}】已配置浏览器池")

    @abstractmethod
    async def _collect_once(self) -> None:
        """
        单次采集逻辑（子类必须实现）

        子类实现具体的采集逻辑，可以使用：
        - self._browser: 浏览器实例（Browser对象）
        - self.config: 采集器配置
        - self.collector_name: 采集器名称（用于日志）

        示例：
            async def _collect_once(self):
                page = await self._browser.new_page()
                try:
                    await page.goto('https://example.com')
                    # ... 采集逻辑
                finally:
                    await page.close()
        """
        pass
