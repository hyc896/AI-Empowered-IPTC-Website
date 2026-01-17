# -*- coding: utf-8 -*-

"""
CNR地方新闻页面HTML结构详细调试
"""

import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)

async def debug_html_structure():
    """调试HTML结构"""
    url = "https://news.cnr.cn/local/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print(f"访问: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        # 查找包含"北京"的元素并分析其父元素结构
        beijing_element = await page.query_selector('text="北京"')
        if beijing_element:
            print("\n找到'北京'元素，分析结构:")

            # 获取父元素链
            parent_html = await page.evaluate('''(element) => {
                let html = '';
                let current = element;
                for (let i = 0; i < 5; i++) {
                    if (!current) break;
                    const tag = current.tagName.toLowerCase();
                    const classes = current.className ? '.' + current.className.split(' ').join('.') : '';
                    const id = current.id ? '#' + current.id : '';
                    html += `Level ${i}: <${tag}${id}${classes}>\\n`;
                    current = current.parentElement;
                }
                return html;
            }''', beijing_element)
            print(parent_html)

            # 获取北京元素的父容器
            parent_div = await beijing_element.evaluate_handle('element => element.closest("div")')
            if parent_div:
                # 检查这个div是否包含ul>li>a结构
                has_ul = await parent_div.evaluate('div => div.querySelector("ul > li > a") !== null')
                print(f"\n父div包含ul>li>a结构: {has_ul}")

                if has_ul:
                    # 获取该div的HTML
                    html = await parent_div.evaluate('div => div.outerHTML')
                    print(f"\n父div的HTML（前2000字符）:\n{html[:2000]}")

        # 尝试直接查找所有新闻链接
        print("\n\n查找所有可能的新闻链接:")
        links = await page.query_selector_all('a[href*="/native/"]')
        print(f"找到 {len(links)} 个包含'/native/'的链接")
        for i, link in enumerate(links[:10], 1):
            href = await link.get_attribute('href')
            text = await link.inner_text()
            text = text[:50].replace('\n', ' ')
            print(f"  [{i}] {text}")
            print(f"      {href}")

        # 尝试查找包含省份名称和新闻链接的容器
        print("\n\n查找省份容器:")
        # 查找同时包含省份名和新闻链接的div
        province_divs = await page.query_selector_all('div:has(p):has(ul > li > a)')
        print(f"找到 {len(province_divs)} 个同时包含p和ul>li>a的div")

        for i, div in enumerate(province_divs[:3], 1):
            try:
                # 获取p标签的文本
                p_elem = await div.query_selector('p')
                if p_elem:
                    p_text = await p_elem.inner_text()
                    print(f"\n容器 {i} 的p标签文本: {p_text.strip()}")

                # 获取链接数量
                links_in_div = await div.query_selector_all('ul > li > a')
                print(f"  包含 {len(links_in_div)} 个链接")

                # 显示前3个链接
                for j, link in enumerate(links_in_div[:3], 1):
                    text = await link.inner_text()
                    href = await link.get_attribute('href')
                    print(f"    [{j}] {text[:50]}")
                    print(f"        {href}")
            except Exception as e:
                print(f"  错误: {e}")

        print("\n按任意键关闭浏览器...")
        await asyncio.sleep(30)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_html_structure())
