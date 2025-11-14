# -*- coding: utf-8 -*-

"""
测试RAND Corporation完整文章列表访问
"""

import asyncio
import sys
from playwright.async_api import async_playwright

async def test_rand_full_list():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        # 尝试访问主AI话题页
        try:
            print('Testing main AI topic page...')
            await page.goto('https://www.rand.org/topics/artificial-intelligence.html', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)

            # 检查是否有"View All"或"See More"按钮
            view_all_btn = await page.query_selector('a:has-text("View All"), a:has-text("See More"), a:has-text("See All"), .view-all')
            if view_all_btn:
                view_all_url = await view_all_btn.get_attribute('href')
                print(f'Found "View All" button: {view_all_url}')

                if not view_all_url.startswith('http'):
                    view_all_url = f'https://www.rand.org{view_all_url}'

                print(f'Navigating to full list: {view_all_url}')
                await page.goto(view_all_url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)
            else:
                print('No "View All" button found, trying topic browse page...')
                # 尝试访问话题分类页
                await page.goto('https://www.rand.org/topics/artificial-intelligence.html?productsPerPage=100', wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)

            # 统计当前页面的文章数量
            articles = await page.query_selector_all('ul.teasers li[data-content-id], .product-item, .search-result')
            print(f'Found {len(articles)} articles on current page')

            # 检查分页
            pagination = await page.query_selector('.pagination, .pager, [class*="pagination"]')
            if pagination:
                print('Pagination found!')
                page_links = await pagination.query_selector_all('a')
                print(f'Found {len(page_links)} page links')

                # 提取分页链接
                for idx, link in enumerate(page_links[:5], 1):
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    print(f'Page link {idx}: {text.strip()} -> {href}')

            # 检查是否有无限滚动
            print('\nTesting infinite scroll...')
            initial_count = len(articles)
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(3)

            articles_after_scroll = await page.query_selector_all('ul.teasers li[data-content-id], .product-item, .search-result')
            print(f'After scroll: {len(articles_after_scroll)} articles')

            if len(articles_after_scroll) > initial_count:
                print('Infinite scroll detected!')
            else:
                print('No infinite scroll')

        except Exception as e:
            print(f'Error: {e}')
        finally:
            await browser.close()

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(test_rand_full_list())
