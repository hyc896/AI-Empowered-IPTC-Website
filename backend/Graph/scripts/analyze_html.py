# -*- coding: utf-8 -*-
"""
分析epub文件的HTML结构
"""
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import json

def analyze_html_structure(epub_path):
    """分析HTML结构，找出章节标题的模式"""
    try:
        book = epub.read_epub(epub_path)

        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), 'html.parser')

                # 获取前5000个字符的HTML结构
                html_text = str(soup)[:5000]

                # 保存到文件
                with open('html_structure_sample.txt', 'w', encoding='utf-8') as f:
                    f.write(html_text)

                print("HTML structure sample saved to: html_structure_sample.txt")

                # 查找所有段落标签
                paragraphs = soup.find_all('p')[:20]

                print(f"\nFound {len(soup.find_all('p'))} paragraphs total")
                print("\nFirst 20 paragraphs:")

                for i, p in enumerate(paragraphs, 1):
                    text = p.get_text().strip()[:100]
                    classes = p.get('class', [])
                    style = p.get('style', '')

                    if text:
                        print(f"\n{i}. Text: {text}")
                        if classes:
                            print(f"   Classes: {classes}")
                        if style:
                            print(f"   Style: {style[:100]}")

                break

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    epub_path = r"d:\AI-Empowered IPTC Website\毛泽东思想和中国特色社会主义理论体系概论（2023）【数字版】.epub"

    print("Analyzing HTML structure...")
    analyze_html_structure(epub_path)
