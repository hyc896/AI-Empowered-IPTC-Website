# -*- coding: utf-8 -*-

"""
CNR地方新闻页面结构调试脚本
"""

import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.DEBUG)

async def debug_page_structure():
    """调试页面结构"""
    url = "https://news.cnr.cn/local/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print(f"访问: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        # 尝试多种选择器
        selectors_to_try = [
            ('原XPath转换的选择器', 'body > div:first-child > div:nth-child(3) > div:nth-child(3) > div:first-child > div'),
            ('所有包含p标签的div', 'div:has(> p)'),
            ('所有包含ul的div', 'div:has(> ul)'),
            ('所有div', 'div'),
            ('body下的第一层div', 'body > div'),
        ]

        for name, selector in selectors_to_try:
            try:
                elements = await page.query_selector_all(selector)
                print(f"\n{name}: {selector}")
                print(f"  找到 {len(elements)} 个元素")

                if len(elements) > 0 and len(elements) < 50:
                    for i, elem in enumerate(elements[:5], 1):
                        text = await elem.inner_text()
                        text = text[:100].replace('\n', ' ')
                        print(f"    [{i}] {text}")
            except Exception as e:
                print(f"  错误: {e}")

        # 尝试查找包含省份名称的元素
        print("\n\n查找包含省份名称的元素:")
        provinces = ['北京', '上海', '广东', '浙江', '四川']
        for province in provinces:
            elements = await page.query_selector_all(f'text="{province}"')
            print(f"  包含'{province}'的元素: {len(elements)}个")

        print("\n按任意键关闭浏览器...")
        await asyncio.sleep(30)  # 保持30秒以便观察

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_page_structure())
