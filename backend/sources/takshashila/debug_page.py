# -*- coding: utf-8 -*-

"""
调试Takshashila网页结构
"""

import asyncio
from playwright.async_api import async_playwright


async def debug_page():
    """调试页面结构"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ]
        )

        page = await browser.new_page()

        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })

        try:
            print("正在访问页面...")
            await page.goto('https://takshashila.org.in/pages/publications/', wait_until="networkidle", timeout=60000)

            print("等待JavaScript加载...")
            await asyncio.sleep(10)

            # 保存页面HTML
            html = await page.content()
            with open('takshashila_page.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("页面HTML已保存到 takshashila_page.html")

            # 截图
            await page.screenshot(path='takshashila_page.png', full_page=True)
            print("页面截图已保存到 takshashila_page.png")

            # 检查列表容器
            list_container = await page.query_selector("#listing-publications-list")
            print(f"列表容器存在: {list_container is not None}")

            if list_container:
                # 检查.list元素
                list_elem = await page.query_selector("#listing-publications-list .list")
                print(f".list元素存在: {list_elem is not None}")

                # 检查li元素
                items = await page.query_selector_all("#listing-publications-list .list > li")
                print(f"找到 {len(items)} 个li元素")

                # 检查其他可能的选择器
                items2 = await page.query_selector_all("#listing-publications-list li")
                print(f"找到 {len(items2)} 个li元素（无>选择器）")

                items3 = await page.query_selector_all(".listing")
                print(f"找到 {len(items3)} 个.listing元素")

        except Exception as e:
            print(f"错误: {e}")
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_page())
