"""
图书馆书籍爬虫
用于爬取 mfindecupl.libsp.cn 的书籍信息
"""

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import time
import csv
from datetime import datetime

class LibspCrawler:
    def __init__(self):
        self.base_url = "https://mfindecupl.libsp.cn"
        self.books = []

    def setup_driver(self):
        """配置浏览器驱动"""
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')  # 调试时可注释掉
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        return driver

    def crawl_books(self, max_pages=5):
        """爬取书籍信息"""
        driver = self.setup_driver()

        try:
            print(f"正在访问 {self.base_url}/#/Home")
            driver.get(f"{self.base_url}/#/Home")

            # 等待页面加载
            time.sleep(3)

            for page in range(max_pages):
                print(f"\n正在爬取第 {page + 1} 页...")

                # 等待书籍元素加载
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                    )
                except:
                    print("页面加载超时")
                    break

                # 获取页面HTML
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')

                # 尝试多种选择器查找书籍元素
                selectors = [
                    {'class': 'book-item'},
                    {'class': 'book-card'},
                    {'class': 'item'},
                    '[class*="book"]',
                    '[class*="card"]'
                ]

                books_found = False
                for selector in selectors:
                    if isinstance(selector, dict):
                        elements = soup.find_all(attrs=selector)
                    else:
                        elements = soup.select(selector)

                    if elements:
                        print(f"  使用选择器 {selector} 找到 {len(elements)} 个元素")
                        self.parse_books(elements)
                        books_found = True
                        break

                if not books_found:
                    print("  未找到书籍元素，尝试分析页面结构...")
                    self.analyze_page_structure(soup)

                # 尝试翻页
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR,
                        "[class*='next'], [class*='下一页'], button:contains('下一页')")
                    next_button.click()
                    time.sleep(2)
                except:
                    print("  没有找到下一页按钮")
                    break

        finally:
            driver.quit()

        return self.books

    def parse_books(self, elements):
        """解析书籍元素"""
        for elem in elements:
            book = {}

            # 提取标题
            title_elem = elem.find(['h1', 'h2', 'h3', 'h4', 'h5'], class_=lambda x: x and 'title' in x.lower()) or \
                         elem.find(class_=lambda x: x and 'title' in x.lower())
            if title_elem:
                book['title'] = title_elem.get_text(strip=True)

            # 提取作者
            author_elem = elem.find(class_=lambda x: x and 'author' in x.lower())
            if author_elem:
                book['author'] = author_elem.get_text(strip=True)

            # 提取封面
            img_elem = elem.find('img')
            if img_elem and img_elem.get('src'):
                book['cover'] = img_elem['src']

            # 提取链接
            link_elem = elem.find('a')
            if link_elem and link_elem.get('href'):
                book['link'] = link_elem['href']

            if book:
                self.books.append(book)
                print(f"    - {book.get('title', '未知标题')}")

    def analyze_page_structure(self, soup):
        """分析页面结构"""
        print("\n  页面结构分析:")

        # 查找所有class包含book的元素
        book_classes = set()
        for elem in soup.find_all(class_=True):
            for cls in elem.get('class', []):
                if 'book' in cls.lower() or 'item' in cls.lower() or 'card' in cls.lower():
                    book_classes.add(cls)

        if book_classes:
            print(f"    可能的书籍class: {', '.join(book_classes)}")

    def save_to_csv(self, filename=None):
        """保存为CSV文件"""
        if not filename:
            filename = f"books_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        if not self.books:
            print("没有数据可保存")
            return

        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ['title', 'author', 'cover', 'link']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.books)

        print(f"\n数据已保存到 {filename}")
        print(f"共爬取 {len(self.books)} 本书籍")

    def save_to_json(self, filename=None):
        """保存为JSON文件"""
        if not filename:
            filename = f"books_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.books, f, ensure_ascii=False, indent=2)

        print(f"\n数据已保存到 {filename}")

if __name__ == "__main__":
    crawler = LibspCrawler()

    print("=" * 60)
    print("开始爬取书籍信息")
    print("=" * 60)

    books = crawler.crawl_books(max_pages=3)

    if books:
        crawler.save_to_csv()
        crawler.save_to_json()
    else:
        print("\n未爬取到任何书籍数据")
        print("建议:")
        print("1. 手动访问网站检查是否需要登录")
        print("2. 检查网站是否有反爬虫机制")
        print("3. 使用浏览器开发者工具查看实际的API请求")
