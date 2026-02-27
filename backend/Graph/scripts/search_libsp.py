"""
直接访问搜索页面并爬取
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import json
import csv
from datetime import datetime

class LibspSearchCrawler:
    def __init__(self):
        self.base_url = "https://mfindecupl.libsp.cn"
        self.books = []

    def setup_driver(self, headless=True):
        """
        设置 Chrome 驱动

        Args:
            headless: 是否使用无头模式（默认True，不显示浏览器窗口）
        """
        options = webdriver.ChromeOptions()

        if headless:
            # 无头模式配置
            options.add_argument('--headless=new')  # 新版无头模式
            options.add_argument('--disable-gpu')  # 禁用GPU加速
            options.add_argument('--no-sandbox')  # 绕过操作系统沙箱
            options.add_argument('--disable-dev-shm-usage')  # 解决资源限制

        # 通用配置
        options.add_argument('--disable-blink-features=AutomationControlled')  # 隐藏自动化特征
        options.add_argument('--window-size=1920,1080')  # 设置窗口大小
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # 禁用不必要的功能以提高性能
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-images')  # 不加载图片，提高速度
        options.add_experimental_option('excludeSwitches', ['enable-logging'])  # 禁用日志
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)

        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def search_books(self, keyword, fetch_details=False, max_details=3):
        """
        搜索书籍

        Args:
            keyword: 搜索关键词
            fetch_details: 是否获取书籍详细信息
            max_details: 最多获取多少本书的详细信息（避免耗时过长）
        """
        driver = self.setup_driver()

        try:
            print(f"访问搜索页面...")
            driver.get(f"{self.base_url}/#/searchList")
            time.sleep(2)

            print(f"输入搜索关键词: {keyword}")
            search_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='search'], input.am-search-value, input[placeholder*='检索']"))
            )

            search_input.clear()
            search_input.send_keys(keyword)
            search_input.send_keys(Keys.RETURN)

            print("等待搜索结果...")
            time.sleep(3)

            # 滚动加载更多
            for i in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)

            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # 查找所有可能的书籍元素
            all_elements = soup.find_all(class_=True)
            book_elements = []

            for elem in all_elements:
                classes = ' '.join(elem.get('class', []))
                if any(keyword in classes.lower() for keyword in ['book', 'item', 'card', 'result']):
                    if elem.find('img') or elem.find(class_=lambda x: x and 'title' in str(x).lower()):
                        book_elements.append(elem)

            print(f"找到 {len(book_elements)} 个书籍元素")

            for elem in book_elements:
                book = {}

                # 标题
                for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'div', 'span', 'p']:
                    title_elem = elem.find(tag, class_=lambda x: x and 'title' in str(x).lower())
                    if title_elem:
                        book['title'] = title_elem.get_text(strip=True)
                        break

                if not book.get('title'):
                    title_elem = elem.find(string=True, recursive=False)
                    if title_elem:
                        book['title'] = str(title_elem).strip()

                # 作者
                author_elem = elem.find(class_=lambda x: x and 'author' in str(x).lower())
                if author_elem:
                    book['author'] = author_elem.get_text(strip=True)

                # 封面
                img_elem = elem.find('img')
                if img_elem:
                    book['cover'] = img_elem.get('src') or img_elem.get('data-src')

                # 链接
                link_elem = elem.find('a')
                if link_elem:
                    book['link'] = link_elem.get('href')

                if book.get('title') and len(book['title']) > 1:
                    self.books.append(book)
                    print(f"  - {book['title']}")

            # 保存完整HTML用于调试
            with open("search_result.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"\n页面HTML已保存到 search_result.html")

        finally:
            driver.quit()

        # 如果需要获取详细信息
        if fetch_details and self.books:
            print(f"\n开始获取书籍详细信息（最多 {max_details} 本）...")
            for i, book in enumerate(self.books[:max_details]):
                if book.get('link'):
                    print(f"[{i+1}/{min(max_details, len(self.books))}] 获取《{book['title']}》的详细信息...")
                    detail = self.get_book_detail(book['link'])
                    if detail:
                        # 合并详细信息到书籍数据
                        book.update(detail)
                        print(f"  ✓ 成功获取详细信息")
                    else:
                        print(f"  ✗ 获取详细信息失败")
                    time.sleep(1)  # 避免请求过快

        return self.books

    def get_book_detail(self, book_url):
        """获取单本书的详细信息"""
        driver = self.setup_driver()

        try:
            print(f"访问书籍详情页: {book_url}")

            # 如果是相对路径，补全为完整URL
            if book_url.startswith('/'):
                book_url = self.base_url + book_url
            elif book_url.startswith('#'):
                book_url = self.base_url + '/' + book_url

            driver.get(book_url)
            time.sleep(3)  # 等待页面加载

            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            detail = {}

            # 提取书名
            title_selectors = [
                ('h1', None),
                ('h2', None),
                ('div', lambda x: x and 'title' in str(x).lower()),
                ('span', lambda x: x and 'title' in str(x).lower())
            ]

            for tag, class_filter in title_selectors:
                if class_filter:
                    elem = soup.find(tag, class_=class_filter)
                else:
                    elem = soup.find(tag)
                if elem:
                    detail['title'] = elem.get_text(strip=True)
                    break

            # 提取作者
            author_keywords = ['author', '作者', 'writer']
            for keyword in author_keywords:
                author_elem = soup.find(class_=lambda x: x and keyword in str(x).lower())
                if not author_elem:
                    author_elem = soup.find(string=lambda x: x and keyword in str(x).lower())
                    if author_elem:
                        author_elem = author_elem.parent
                if author_elem:
                    detail['author'] = author_elem.get_text(strip=True).replace('作者:', '').replace('作者：', '').strip()
                    break

            # 提取出版社
            publisher_keywords = ['publisher', '出版社', 'press']
            for keyword in publisher_keywords:
                pub_elem = soup.find(class_=lambda x: x and keyword in str(x).lower())
                if not pub_elem:
                    pub_elem = soup.find(string=lambda x: x and keyword in str(x).lower())
                    if pub_elem:
                        pub_elem = pub_elem.parent
                if pub_elem:
                    detail['publisher'] = pub_elem.get_text(strip=True).replace('出版社:', '').replace('出版社：', '').strip()
                    break

            # 提取ISBN
            isbn_elem = soup.find(string=lambda x: x and 'isbn' in str(x).lower())
            if isbn_elem:
                isbn_text = isbn_elem.parent.get_text(strip=True)
                import re
                isbn_match = re.search(r'ISBN[:\s]*([0-9\-]+)', isbn_text, re.IGNORECASE)
                if isbn_match:
                    detail['isbn'] = isbn_match.group(1)

            # 提取封面图片
            img_elem = soup.find('img', class_=lambda x: x and ('cover' in str(x).lower() or 'book' in str(x).lower()))
            if not img_elem:
                img_elem = soup.find('img')
            if img_elem:
                detail['cover'] = img_elem.get('src') or img_elem.get('data-src')

            # 提取简介
            desc_keywords = ['description', 'summary', 'intro', '简介', '内容简介', '内容介绍']
            for keyword in desc_keywords:
                desc_elem = soup.find(class_=lambda x: x and keyword in str(x).lower())
                if not desc_elem:
                    desc_elem = soup.find(string=lambda x: x and keyword in str(x).lower())
                    if desc_elem:
                        desc_elem = desc_elem.find_next(['div', 'p'])
                if desc_elem:
                    detail['description'] = desc_elem.get_text(strip=True)
                    break

            # 保存详情页HTML用于调试
            with open("book_detail.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"详情页HTML已保存到 book_detail.html")

            return detail

        except Exception as e:
            print(f"获取书籍详情失败: {str(e)}")
            return None
        finally:
            driver.quit()

    def save_to_json(self, filename=None):
        if not filename:
            filename = f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.books, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到 {filename}")

    def save_to_csv(self, filename=None):
        if not filename:
            filename = f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        if not self.books:
            return
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ['title', 'author', 'cover', 'link']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.books)
        print(f"数据已保存到 {filename}")

if __name__ == "__main__":
    import sys

    crawler = LibspSearchCrawler()

    # 支持命令行参数
    if len(sys.argv) > 1:
        keyword = sys.argv[1]
    else:
        keyword = input("请输入搜索关键词: ") or "法学"

    print("="*60)
    print(f"开始搜索: {keyword}")
    print("="*60)

    books = crawler.search_books(keyword)

    if books:
        # 如果是命令行调用，只输出 JSON 到 stdout
        if len(sys.argv) > 1:
            print(json.dumps(books, ensure_ascii=False))
        else:
            # 交互式调用，保存文件
            crawler.save_to_json()
            crawler.save_to_csv()
            print(f"\n共爬取 {len(books)} 本书籍")
    else:
        if len(sys.argv) > 1:
            print(json.dumps([], ensure_ascii=False))
        else:
            print("\n未找到搜索结果，请检查 search_result.html 文件")
