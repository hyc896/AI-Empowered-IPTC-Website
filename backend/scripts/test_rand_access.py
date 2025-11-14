# -*- coding: utf-8 -*-

"""
测试RAND Corporation网站访问
"""

import asyncio
import sys
from playwright.async_api import async_playwright

async def test_rand():
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
            print('Navigating to RAND AI page...')
            await page.goto('https://www.rand.org/topics/artificial-intelligence.html', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(5)

            content = await page.content()
            if '403' in content or 'ERROR' in content:
                print('ERROR: 403 or blocked')
                print(content[:1000])
            else:
                print('SUCCESS: Page loaded')

                # 尝试查找文章列表
                articles = await page.query_selector_all('ul.teasers li[data-content-id]')
                print(f'Found {len(articles)} articles with selector: ul.teasers li[data-content-id]')

                if articles:
                    print(f'\nAnalyzing first 3 articles:')
                    for idx, article in enumerate(articles[:3], 1):
                        print(f'\n--- Article {idx} ---')

                        # 提取content-id
                        content_id = await article.get_attribute('data-content-id')
                        print(f'Content ID: {content_id}')

                        # 提取标题
                        title_elem = await article.query_selector('h3.title')
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
                        date_elem = await article.query_selector('p.date')
                        if date_elem:
                            date = await date_elem.inner_text()
                            print(f'Date: {date.strip()}')

                    # 测试点击第一篇文章，查看详情页结构
                    print('\n\n=== Testing detail page structure ===')
                    first_link = await articles[0].query_selector('a[href]')
                    detail_url = await first_link.get_attribute('href')
                    if not detail_url.startswith('http'):
                        detail_url = f'https://www.rand.org{detail_url}'

                    print(f'Opening detail page: {detail_url}')
                    await page.goto(detail_url, wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(3)

                    # 提取详情页内容
                    # 尝试提取作者
                    author_elem = await page.query_selector('.author, .authors, [class*="author"]')
                    if author_elem:
                        author = await author_elem.inner_text()
                        print(f'Author: {author.strip()[:200]}')

                    # 提取摘要
                    summary_elem = await page.query_selector('.abstract, .summary, [class*="abstract"]')
                    if summary_elem:
                        summary = await summary_elem.inner_text()
                        print(f'Summary: {summary.strip()[:300]}')

                    # 提取正文
                    content_elems = await page.query_selector_all('.product-main p, article p, .content p')
                    if content_elems:
                        print(f'Found {len(content_elems)} paragraphs in content')
                        first_paras = []
                        for para in content_elems[:3]:
                            text = await para.inner_text()
                            if text.strip():
                                first_paras.append(text.strip())
                        print(f'First 3 paragraphs: {" | ".join(first_paras)[:300]}')

                else:
                    print('No articles found')
        except Exception as e:
            print(f'Error: {e}')
        finally:
            await browser.close()

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(test_rand())
