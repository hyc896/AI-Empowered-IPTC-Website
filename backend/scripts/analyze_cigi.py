"""
临时脚本：分析CIGI网站结构
"""
import asyncio
from playwright.async_api import async_playwright
import sys
import os

# 添加backend到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


async def analyze_cigi():
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )

        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        )

        page = await context.new_page()

        try:
            print("正在导航到CIGI AI主题页...")
            await page.goto('https://www.cigionline.org/topics/artificial-intelligence/',
                          wait_until='networkidle',
                          timeout=60000)

            print("页面加载成功！")

            # 等待内容加载
            await page.wait_for_timeout(5000)

            # 截图
            await page.screenshot(path='d:\\TechWork\\message_platform\\cigi_page.png')
            print("截图已保存")

            # 获取页面标题
            title = await page.title()
            print(f"页面标题: {title}")

            # 查找文章列表容器
            print("\n查找文章列表...")

            # 常见的文章容器类名
            possible_selectors = [
                'article',
                '.article',
                '.post',
                '.publication',
                '.content-item',
                '.card',
                '[class*="article"]',
                '[class*="post"]',
                '[class*="publication"]',
                '[class*="content"]'
            ]

            for selector in possible_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        print(f"\n找到选择器: {selector} - 数量: {len(elements)}")

                        # 获取第一个元素的HTML
                        if len(elements) > 0:
                            html = await elements[0].inner_html()
                            print(f"第一个元素的HTML（前500字符）:\n{html[:500]}")
                except Exception as e:
                    pass

            # 获取整个页面的HTML
            html = await page.content()

            # 保存HTML
            with open('d:\\TechWork\\message_platform\\cigi_page.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("\nHTML已保存到 cigi_page.html")

            # 查找包含"article"或"publication"的类名
            print("\n查找包含特定关键词的元素...")
            result = await page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('[class*="article"], [class*="publication"], [class*="post"], [class*="content"]');
                    return Array.from(elements).slice(0, 5).map(el => ({
                        tag: el.tagName,
                        className: el.className,
                        id: el.id,
                        textPreview: el.textContent.substring(0, 100)
                    }));
                }
            """)

            print("找到的元素:")
            for item in result:
                print(f"  Tag: {item['tag']}, Class: {item['className']}, ID: {item['id']}")
                print(f"  Text preview: {item['textPreview']}")
                print()

        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await browser.close()


if __name__ == '__main__':
    # Windows环境需要设置事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(analyze_cigi())
