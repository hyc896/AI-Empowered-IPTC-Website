# -*- coding: utf-8 -*-

"""
通用页面全量加载工具
支持无限滚动、"加载更多"按钮、传统分页三种模式
"""

import asyncio
import logging
from typing import Optional
from playwright.async_api import Page

logger = logging.getLogger(__name__)


class PageLoader:
    """页面全量加载器"""

    @staticmethod
    async def load_all_content(
        page: Page,
        item_selector: str,
        max_scrolls: int = 50,
        scroll_delay: float = 2.0,
        load_more_selectors: list = None,
        next_page_selectors: list = None
    ) -> int:
        """
        自适应全量加载页面内容

        策略优先级：
        1. 无限滚动检测 → 滚动到底部触发懒加载
        2. "加载更多"按钮 → 循环点击按钮
        3. 传统分页 → 点击下一页链接

        Args:
            page: Playwright Page对象
            item_selector: 文章元素选择器（用于检测数量变化）
            max_scrolls: 最大滚动次数（防止死循环）
            scroll_delay: 每次滚动后的等待时间（秒）
            load_more_selectors: "加载更多"按钮的可能选择器列表
            next_page_selectors: "下一页"链接的可能选择器列表

        Returns:
            最终加载的元素数量
        """
        if load_more_selectors is None:
            load_more_selectors = [
                'button:has-text("Load More")',
                'button:has-text("Show More")',
                'a:has-text("Load More")',
                'a:has-text("Show More")',
                '[class*="load-more"]',
                '[class*="show-more"]',
                '[id*="load-more"]'
            ]

        if next_page_selectors is None:
            next_page_selectors = [
                'a:has-text("Next")',
                'a[rel="next"]',
                '.pagination a:has-text("›")',
                '.pagination a:has-text(">")',
                '[class*="next-page"]'
            ]

        initial_count = await PageLoader._count_items(page, item_selector)
        logger.info(f"【PageLoader】初始元素数量: {initial_count}")

        # 策略1: 尝试"加载更多"按钮
        final_count = await PageLoader._try_load_more_button(
            page, item_selector, load_more_selectors, max_scrolls, scroll_delay
        )

        if final_count > initial_count:
            logger.info(f"【PageLoader】使用"加载更多"按钮模式，最终元素数量: {final_count}")
            return final_count

        # 策略2: 尝试无限滚动
        final_count = await PageLoader._try_infinite_scroll(
            page, item_selector, max_scrolls, scroll_delay
        )

        if final_count > initial_count:
            logger.info(f"【PageLoader】使用无限滚动模式，最终元素数量: {final_count}")
            return final_count

        # 策略3: 尝试传统分页
        final_count = await PageLoader._try_pagination(
            page, item_selector, next_page_selectors, max_scrolls, scroll_delay
        )

        logger.info(f"【PageLoader】最终元素数量: {final_count}（初始: {initial_count}）")
        return final_count

    @staticmethod
    async def _count_items(page: Page, selector: str) -> int:
        """统计元素数量"""
        try:
            elements = await page.query_selector_all(selector)
            return len(elements)
        except Exception as e:
            logger.error(f"统计元素失败: {e}")
            return 0

    @staticmethod
    async def _try_load_more_button(
        page: Page,
        item_selector: str,
        button_selectors: list,
        max_clicks: int,
        delay: float
    ) -> int:
        """
        尝试"加载更多"按钮模式

        Returns:
            加载后的元素数量
        """
        clicks = 0
        prev_count = await PageLoader._count_items(page, item_selector)

        for _ in range(max_clicks):
            button_found = False

            # 尝试所有可能的按钮选择器
            for selector in button_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        # 检查按钮是否可见且可点击
                        is_visible = await button.is_visible()
                        is_enabled = await button.is_enabled()

                        if is_visible and is_enabled:
                            logger.debug(f"找到加载更多按钮: {selector}")
                            await button.click()
                            button_found = True
                            clicks += 1

                            # 等待内容加载
                            await asyncio.sleep(delay)

                            # 检查元素数量是否增加
                            current_count = await PageLoader._count_items(page, item_selector)
                            if current_count > prev_count:
                                logger.debug(f"加载更多成功: {prev_count} → {current_count}")
                                prev_count = current_count
                            else:
                                logger.debug("元素数量未增加，可能已加载完毕")
                                return current_count

                            break
                except Exception:
                    continue

            if not button_found:
                break

        if clicks > 0:
            logger.info(f"【加载更多按钮】点击 {clicks} 次")

        return prev_count

    @staticmethod
    async def _try_infinite_scroll(
        page: Page,
        item_selector: str,
        max_scrolls: int,
        delay: float
    ) -> int:
        """
        尝试无限滚动模式

        Returns:
            加载后的元素数量
        """
        prev_count = await PageLoader._count_items(page, item_selector)
        no_change_count = 0

        for scroll_num in range(max_scrolls):
            # 滚动到页面底部
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(delay)

            # 检查元素数量
            current_count = await PageLoader._count_items(page, item_selector)

            if current_count > prev_count:
                logger.debug(f"滚动 {scroll_num + 1}: {prev_count} → {current_count} 项")
                prev_count = current_count
                no_change_count = 0
            else:
                no_change_count += 1
                # 连续3次滚动无变化，认为已加载完毕
                if no_change_count >= 3:
                    logger.debug(f"连续{no_change_count}次滚动无变化，停止滚动")
                    break

        if prev_count > await PageLoader._count_items(page, item_selector):
            logger.info(f"【无限滚动】共滚动 {scroll_num + 1} 次")

        return prev_count

    @staticmethod
    async def _try_pagination(
        page: Page,
        item_selector: str,
        next_page_selectors: list,
        max_pages: int,
        delay: float
    ) -> int:
        """
        尝试传统分页模式

        Returns:
            加载后的元素数量（注意：分页模式会导航到新页面，原页面元素会丢失）
        """
        pages_loaded = 0
        total_count = await PageLoader._count_items(page, item_selector)

        for page_num in range(max_pages):
            next_button_found = False

            # 尝试所有可能的"下一页"选择器
            for selector in next_page_selectors:
                try:
                    next_button = await page.query_selector(selector)
                    if next_button:
                        is_visible = await next_button.is_visible()
                        is_enabled = await next_button.is_enabled()

                        if is_visible and is_enabled:
                            logger.debug(f"找到下一页按钮: {selector}")
                            await next_button.click()
                            next_button_found = True
                            pages_loaded += 1

                            # 等待页面导航完成
                            await page.wait_for_load_state("domcontentloaded")
                            await asyncio.sleep(delay)

                            # 统计当前页元素
                            current_count = await PageLoader._count_items(page, item_selector)
                            total_count += current_count
                            logger.debug(f"加载第 {page_num + 2} 页，新增 {current_count} 项")

                            break
                except Exception:
                    continue

            if not next_button_found:
                break

        if pages_loaded > 0:
            logger.info(f"【传统分页】共加载 {pages_loaded + 1} 页")

        return total_count
