# -*- coding: utf-8 -*-
"""
从epub文件中提取章节结构和知识点
只提取标题和结构，不复制完整内容
"""
import sys
from pathlib import Path
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import json
import re

def extract_chapter_structure(epub_path):
    """提取章节结构和知识点"""
    try:
        book = epub.read_epub(epub_path)

        chapters = []

        # 提取主要内容
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), 'html.parser')

                # 查找所有标题（h1-h6）
                headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

                for heading in headings:
                    text = heading.get_text().strip()

                    # 过滤掉空标题和过短的标题
                    if text and len(text) > 2:
                        level = int(heading.name[1])  # h1->1, h2->2, etc.

                        chapters.append({
                            "level": level,
                            "title": text,
                            "type": "chapter" if level <= 2 else "section"
                        })

        return chapters

    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    epub_path = r"d:\AI-Empowered IPTC Website\毛泽东思想和中国特色社会主义理论体系概论（2023）【数字版】.epub"

    print("Extracting chapter structure...")
    chapters = extract_chapter_structure(epub_path)

    if chapters:
        # 保存到JSON文件
        output_path = "chapters_structure.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chapters, f, ensure_ascii=False, indent=2)

        print(f"Success! Found {len(chapters)} headings")
        print(f"Structure saved to: {output_path}")
    else:
        print("Extraction failed")
