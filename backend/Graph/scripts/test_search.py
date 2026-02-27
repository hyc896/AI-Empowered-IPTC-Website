"""
测试搜索功能
分析网站的搜索机制
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

options = webdriver.ChromeOptions()
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    print("访问网站...")
    driver.get("https://mfindecupl.libsp.cn/#/Home")
    time.sleep(3)

    # 查找搜索框
    print("\n查找搜索框...")
    search_selectors = [
        "input[type='search']",
        "input[type='text']",
        "input[placeholder*='搜索']",
        "input[placeholder*='search']",
        ".search-input",
        "#search"
    ]

    search_box = None
    for selector in search_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"找到搜索框: {selector}, 共{len(elements)}个")
                for i, elem in enumerate(elements):
                    print(f"  [{i}] placeholder: {elem.get_attribute('placeholder')}")
                    print(f"      class: {elem.get_attribute('class')}")
                    print(f"      displayed: {elem.is_displayed()}")
                    if elem.is_displayed() and elem.get_attribute('placeholder'):
                        search_box = elem
                        print(f"      ✓ 选中此搜索框")
                        break
                if search_box:
                    break
        except Exception as e:
            print(f"  错误: {e}")

    if search_box:
        print("\n执行搜索...")
        search_box.clear()
        search_box.send_keys("法学")
        search_box.send_keys(Keys.RETURN)

        time.sleep(3)

        print(f"当前URL: {driver.current_url}")

        # 查找搜索结果
        print("\n查找搜索结果...")
        results = driver.find_elements(By.CSS_SELECTOR, "[class*='book'], [class*='item'], [class*='result']")
        print(f"找到 {len(results)} 个结果元素")

        # 保存页面HTML用于分析
        with open("search_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("\n页面HTML已保存到 search_page.html")
    else:
        print("未找到搜索框")

        # 保存页面HTML
        with open("home_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("首页HTML已保存到 home_page.html")

finally:
    driver.quit()
