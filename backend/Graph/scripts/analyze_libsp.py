"""
图书馆网站分析脚本
用于分析 mfindecupl.libsp.cn 的API接口和数据结构
"""

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json
import time

class LibspAnalyzer:
    def __init__(self):
        self.base_url = "https://mfindecupl.libsp.cn"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://mfindecupl.libsp.cn/'
        })

    def analyze_with_selenium(self):
        """使用Selenium分析网站结构和网络请求"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_experimental_option('perfLoggingPrefs', {'enableNetwork': True})
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        try:
            print("正在加载页面...")
            driver.get(f"{self.base_url}/#/Home")
            time.sleep(5)

            # 获取网络日志
            logs = driver.get_log('performance')
            api_requests = []

            for log in logs:
                message = json.loads(log['message'])['message']
                if message['method'] == 'Network.responseReceived':
                    url = message['params']['response']['url']
                    if 'api' in url.lower() or 'json' in url.lower():
                        api_requests.append({
                            'url': url,
                            'status': message['params']['response']['status'],
                            'type': message['params']['response']['mimeType']
                        })

            print("\n发现的API接口:")
            for req in api_requests:
                print(f"  - {req['url']}")
                print(f"    状态: {req['status']}, 类型: {req['type']}")

            # 分析页面结构
            print("\n页面元素分析:")
            try:
                books = driver.find_elements(By.CSS_SELECTOR, "[class*='book'], [class*='item']")
                print(f"  找到 {len(books)} 个可能的书籍元素")
            except:
                pass

            return api_requests

        finally:
            driver.quit()

    def test_common_apis(self):
        """测试常见的API端点"""
        common_endpoints = [
            '/api/books',
            '/api/book/list',
            '/api/search',
            '/api/home',
            '/api/v1/books',
            '/book/list',
            '/search'
        ]

        print("\n测试常见API端点:")
        for endpoint in common_endpoints:
            url = f"{self.base_url}{endpoint}"
            try:
                resp = self.session.get(url, timeout=5)
                if resp.status_code == 200:
                    print(f"  ✓ {endpoint} - 状态码: {resp.status_code}")
                    print(f"    响应长度: {len(resp.text)}")
            except Exception as e:
                pass

if __name__ == "__main__":
    analyzer = LibspAnalyzer()

    print("=" * 60)
    print("开始分析 mfindecupl.libsp.cn")
    print("=" * 60)

    # 方法1: 使用Selenium分析
    try:
        api_requests = analyzer.analyze_with_selenium()
    except Exception as e:
        print(f"Selenium分析失败: {e}")

    # 方法2: 测试常见API
    analyzer.test_common_apis()

    print("\n分析完成!")
