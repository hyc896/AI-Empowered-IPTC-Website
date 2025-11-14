# -*- coding: utf-8 -*-

"""
测试RAND Corporation搜索页面
"""

import asyncio
import sys
from playwright.async_api import async_playwright

async def test_rand_search():
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

        try:
            # 尝试搜索页面
            search_url = 'https://www.rand.org/pubs.html?topic=artificial-intelligence&sortBy=date'
            print(f'Accessing search/pubs page: {search_url}')
            await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(5)

            # 检查文章列表
            selectors_to_try = [
                'ul.teasers li[data-content-id]',
                '.product-item',
                '.search-result',
                '.publication-item',
                'ul.list li',
                '[data-product-id]'
            ]

            for selector in selectors_to_try:
                articles = await page.query_selector_all(selector)
                if articles:
                    print(f'\nFound {len(articles)} articles with selector: {selector}')

                    # 分析前3篇文章
                    for idx, article in enumerate(articles[:3], 1):
                        print(f'\n--- Article {idx} ---')

                        # 提取content-id
                        content_id = await article.get_attribute('data-content-id')
                        print(f'Content ID: {content_id}')

                        # 提取标题
                        title_elem = await article.query_selector('h3.title, h2, h3')
                        if title_elem:
                            title = await title_elem.inner_text()
                            print(f'Title: {title.strip()}')

                        # 提取链接
                        link_elem = await article.query_selector('a[href]')
                        if link_elem:
                            link = await link_elem.get_attribute('href')
                            print(f'Link: {link}')

                        # 提取类型
                        type_elem = await article.query_selector('.type')
                        if type_elem:
                            pub_type = await type_elem.inner_text()
                            print(f'Type: {pub_type.strip()}')

                        # 提取日期
                        date_elem = await article.query_selector('p.date, .date')
                        if date_elem:
                            date = await date_elem.inner_text()
                            print(f'Date: {date.strip()}')

                    # 检查分页
                    print('\n=== Checking pagination ===')
                    pagination = await page.query_selector('.pagination, .pager, [class*="pager"]')
                    if pagination:
                        print('Pagination found!')
                        page_links = await pagination.query_selector_all('a')
                        print(f'Found {len(page_links)} page links')

                        for idx, link in enumerate(page_links[:5], 1):
                            href = await link.get_attribute('href')
                            text = await link.inner_text()
                            print(f'  Page {idx}: {text.strip()} -> {href}')
                    else:
                        print('No pagination found')

                        # 检查"Load More"按钮
                        load_more = await page.query_selector('button:has-text("Load More"), a:has-text("Load More"), .load-more')
                        if load_more:
                            print('Load More button found!')
                        else:
                            print('No Load More button')

                    break
            else:
                print('No articles found with any selector')
                print('\nDumping page content...')
                content = await page.content()
                print(content[:2000])

        except Exception as e:
            print(f'Error: {e}')
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(test_rand_search())
