# -*- coding: utf-8 -*-

"""
快速测试CNAS网页结构
"""

import asyncio
import sys

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.async_api import async_playwright


async def test_scrape():
    url = "https://www.cnas.org/reports"

    print(f"访问: {url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 可视化模式
        page = await browser.new_page()

        await page.goto(url, timeout=30000)
        await asyncio.sleep(5)

        print("查找所有链接...")
        links = await page.query_selector_all('a[href*="/publications/"]')
        print(f"找到 {len(links)} 个出版物链接\n")

        for idx, link in enumerate(links[:5], 1):
            href = await link.get_attribute('href')
            text = (await link.inner_text()).strip()[:80]
            print(f"[{idx}] {text}")
            print(f"    {href}\n")

        await browser.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(test_scrape())
