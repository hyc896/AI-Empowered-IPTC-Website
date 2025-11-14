# -*- coding: utf-8 -*-
"""
Nikkei Asia 采集器调试脚本
用于测试为什么解析到 0 条文章
"""

import asyncio
import re
import json
from playwright.async_api import async_playwright

async def test_scrape():
    url = 'https://asia.nikkei.com/Business/Technology/Artificial-intelligence'

    print("=" * 80)
    print("Nikkei Asia 采集器调试")
    print("=" * 80)
    print(f"目标URL: {url}\n")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)

    context = await browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    page = await context.new_page()

    print("1. 访问页面...")
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(5000)  # 等待 5 秒确保内容加载

    print("2. 获取页面内容...")
    content = await page.content()
    print(f"   页面内容长度: {len(content)} 字符\n")

    print("3. 查找 __NEXT_DATA__ 脚本标签...")
    json_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', content, re.DOTALL)

    if not json_match:
        print("   [NO] 未找到 __NEXT_DATA__ 标签")
        print("\n   尝试查找其他可能的 JSON 数据位置...")

        # 尝试其他匹配模式
        patterns = [
            r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>',
            r'<script[^>]*__NEXT_DATA__[^>]*>(.+?)</script>',
            r'window\.__NEXT_DATA__\s*=\s*({.+?});',
        ]

        for i, pattern in enumerate(patterns, 1):
            alt_match = re.search(pattern, content, re.DOTALL)
            if alt_match:
                print(f"   [YES] 使用备用模式 {i} 找到 JSON 数据")
                json_match = alt_match
                break
    else:
        print("   [YES] 找到 __NEXT_DATA__ 标签\n")

    if not json_match:
        print("   [NO] 所有模式都未匹配到 JSON 数据")

        # 保存页面内容用于调试
        with open('nikkei_debug_page.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("   已保存页面内容到 nikkei_debug_page.html")

        await browser.close()
        await playwright.stop()
        return

    print("4. 解析 JSON 数据...")
    try:
        json_data = json.loads(json_match.group(1))
        print("   [YES] JSON 解析成功\n")
    except json.JSONDecodeError as e:
        print(f"   [NO] JSON 解析失败: {e}")
        await browser.close()
        await playwright.stop()
        return

    print("5. 查找文章数据...")
    print(f"   JSON 顶层键: {list(json_data.keys())}\n")

    # 尝试不同的路径
    paths = [
        ('props.pageProps.stream', lambda d: d.get('props', {}).get('pageProps', {}).get('stream', [])),
        ('props.pageProps.articles', lambda d: d.get('props', {}).get('pageProps', {}).get('articles', [])),
        ('props.pageProps.data.stream', lambda d: d.get('props', {}).get('pageProps', {}).get('data', {}).get('stream', [])),
        ('pageProps.stream', lambda d: d.get('pageProps', {}).get('stream', [])),
    ]

    articles_raw = None
    used_path = None

    for path_name, path_func in paths:
        result = path_func(json_data)
        if result and isinstance(result, list):
            articles_raw = result
            used_path = path_name
            print(f"   [YES] 在路径 '{path_name}' 找到 {len(result)} 条数据\n")
            break
        else:
            print(f"   [NO] 路径 '{path_name}' 无数据或非列表")

    if not articles_raw:
        print("\n   所有路径都未找到文章数据")
        print("   JSON 结构预览:")
        print(json.dumps(json_data, indent=2, ensure_ascii=False)[:2000])

        await browser.close()
        await playwright.stop()
        return

    print("6. 解析文章详情...")
    print(f"   文章数据总数: {len(articles_raw)}\n")

    # 显示前 3 篇文章的原始数据结构
    for i, item in enumerate(articles_raw[:3], 1):
        print(f"   文章 {i} 原始数据键: {list(item.keys())}")
        print(f"   - id: {item.get('id')}")
        print(f"   - headline: {item.get('headline')}")
        print(f"   - path: {item.get('path')}")
        print(f"   - url: {item.get('url')}")
        print(f"   - displayDate: {item.get('displayDate')}")
        print()

    # 测试解析逻辑
    parsed_count = 0
    failed_count = 0

    for item in articles_raw:
        try:
            path = item.get('path', '') or item.get('url', '')
            if not path:
                failed_count += 1
                continue

            title = item.get('headline', '')
            if not title:
                failed_count += 1
                continue

            parsed_count += 1
        except Exception as e:
            failed_count += 1
            print(f"   解析失败: {e}")

    print(f"7. 解析结果统计:")
    print(f"   [SUCCESS] 成功解析: {parsed_count} 篇")
    print(f"   [FAILED] 解析失败: {failed_count} 篇")
    print(f"   [TOTAL] 总计: {len(articles_raw)} 篇")

    await browser.close()
    await playwright.stop()

    print("\n" + "=" * 80)
    print("调试完成")
    print("=" * 80)

if __name__ == '__main__':
    asyncio.run(test_scrape())
