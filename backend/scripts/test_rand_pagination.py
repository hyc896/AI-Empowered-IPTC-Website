# -*- coding: utf-8 -*-

"""
测试RAND Corporation分页机制
"""

import asyncio
import sys
from playwright.async_api import async_playwright

async def test_rand_pagination():
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
            # 访问第一页
            base_url = 'https://www.rand.org/pubs.html?topic=artificial-intelligence&sortBy=date'
            print(f'Page 1: {base_url}')
            await page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)

            articles_page1 = await page.query_selector_all('ul.teasers li[data-content-id]')
            print(f'Page 1: Found {len(articles_page1)} articles')

            # 获取分页信息
            pagination = await page.query_selector('.pagination, .pager, [class*="pager"]')
            if pagination:
                next_link = await pagination.query_selector('a:has-text("NEXT"), a:has-text("Next")')
                if next_link:
                    next_url = await next_link.get_attribute('href')
                    if not next_url.startswith('http'):
                        next_url = f'https://www.rand.org{next_url}'

                    print(f'\nPage 2: {next_url}')
                    await page.goto(next_url, wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(3)

                    articles_page2 = await page.query_selector_all('ul.teasers li[data-content-id]')
                    print(f'Page 2: Found {len(articles_page2)} articles')

                    # 列出第2页的前3篇文章
                    for idx, article in enumerate(articles_page2[:3], 1):
                        content_id = await article.get_attribute('data-content-id')
                        title_elem = await article.query_selector('h3.title, h2, h3')
                        title = ''
                        if title_elem:
                            title = await title_elem.inner_text()
                        print(f'  [{idx}] {content_id}: {title.strip()[:60]}')

                    # 测试直接构造URL（start参数）
                    print('\n=== Testing direct URL construction ===')
                    # start=12表示从第13篇开始（0-based）
                    # 每页12篇，所以start=0,12,24,36...
                    for page_num in range(3):
                        start = page_num * 12
                        test_url = f'https://www.rand.org/pubs.html?topic=artificial-intelligence&sortBy=date&start={start}'
                        print(f'\nPage {page_num+1} (start={start}): {test_url}')
                        await page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
                        await asyncio.sleep(2)

                        articles = await page.query_selector_all('ul.teasers li[data-content-id]')
                        print(f'  Found {len(articles)} articles')

                        if articles:
                            first_article = articles[0]
                            content_id = await first_article.get_attribute('data-content-id')
                            title_elem = await first_article.query_selector('h3.title, h2, h3')
                            title = ''
                            if title_elem:
                                title = await title_elem.inner_text()
                            print(f'  First article: {content_id} - {title.strip()[:60]}')

        except Exception as e:
            print(f'Error: {e}')
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(test_rand_pagination())
