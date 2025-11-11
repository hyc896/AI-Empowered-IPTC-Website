# -*- coding: utf-8 -*-

"""
CNAS采集器简单测试（仅MySQL，不依赖ChromaDB）
"""

import asyncio
import sys
import os
import logging

# Windows控制台UTF-8编码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from backend.database.connection import create_session
from backend.database.entities import CNASMessage
from playwright.async_api import async_playwright


async def simple_scrape_test():
    """简单的网页抓取测试"""
    print("=== CNAS网页抓取测试 ===\n")

    url = "https://www.cnas.org/reports"

    print(f"1. 访问列表页: {url}")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            print("   OK 页面加载成功\n")

            # 尝试提取文章列表
            print("2. 提取文章列表...")

            # 查找所有可能包含文章的元素
            article_elements = await page.query_selector_all('div.row > div[class*="col"], article, .card')
            print(f"   找到 {len(article_elements)} 个候选元素\n")

            # 提取前3个
            articles = []
            for idx, elem in enumerate(article_elements[:5], 1):
                try:
                    # 查找标题链接
                    title_link = await elem.query_selector('a[href*="/publications/"]')
                    if not title_link:
                        continue

                    title = (await title_link.inner_text()).strip()
                    href = await title_link.get_attribute('href')

                    if href and href.startswith('/'):
                        href = f"https://www.cnas.org{href}"

                    # 提取日期
                    date_elem = await elem.query_selector('time, .date, span')
                    date_text = ""
                    if date_elem:
                        date_text = (await date_elem.inner_text()).strip()

                    # 提取作者
                    author_elem = await elem.query_selector('p:has-text("By"), .author')
                    author = ""
                    if author_elem:
                        author = (await author_elem.inner_text()).strip()

                    if title and href:
                        articles.append({
                            'title': title,
                            'url': href,
                            'date': date_text,
                            'author': author
                        })
                        print(f"   [{idx}] {title[:60]}...")
                        print(f"       URL: {href}")
                        print(f"       日期: {date_text}")
                        print(f"       作者: {author}\n")

                except Exception as e:
                    continue

            print(f"OK 成功提取 {len(articles)} 篇文章\n")

            # 测试访问一个详情页
            if articles:
                print("3. 测试访问详情页...")
                test_article = articles[0]
                detail_page = await browser.new_page()

                try:
                    await detail_page.goto(test_article['url'], wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)

                    # 提取正文段落
                    paragraphs = await detail_page.query_selector_all('article p, .entry-content p, .post-content p')
                    content_parts = []

                    for para in paragraphs[:10]:  # 只取前10段
                        text = (await para.inner_text()).strip()
                        if text and len(text) > 30:
                            content_parts.append(text)

                    full_content = '\n\n'.join(content_parts)

                    print(f"   OK 提取到 {len(content_parts)} 段正文")
                    print(f"   总长度: {len(full_content)} 字符")
                    print(f"   前200字: {full_content[:200]}...\n")

                except Exception as e:
                    print(f"   ERROR 详情页访问失败: {e}\n")
                finally:
                    await detail_page.close()

        except Exception as e:
            print(f"ERROR 抓取失败: {e}")
        finally:
            await browser.close()

    print("=== 测试完成 ===")


async def database_test():
    """数据库连接测试"""
    print("\n=== 数据库测试 ===\n")

    try:
        with create_session() as db:
            count = db.query(CNASMessage).count()
            print(f"OK 数据库连接成功")
            print(f"   当前记录数: {count} 条\n")

            if count > 0:
                latest = db.query(CNASMessage).order_by(
                    CNASMessage.crawled_at.desc()
                ).first()

                print("最新记录:")
                print(f"  标题: {latest.title}")
                print(f"  URL: {latest.url}")
                print(f"  抓取时间: {latest.crawled_at}\n")

    except Exception as e:
        print(f"ERROR 数据库连接失败: {e}\n")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(simple_scrape_test())
    asyncio.run(database_test())
