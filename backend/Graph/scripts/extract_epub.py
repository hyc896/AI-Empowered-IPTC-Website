# -*- coding: utf-8 -*-
"""
从epub文件中提取章节结构和内容
"""
import sys
from pathlib import Path
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import json

def extract_epub_structure(epub_path):
    """提取epub文件的章节结构"""
    try:
        book = epub.read_epub(epub_path)

        structure = {
            "title": book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else "未知",
            "author": book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else "未知",
            "chapters": []
        }

        # 提取章节
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                # 解析HTML内容
                soup = BeautifulSoup(item.get_content(), 'html.parser')

                # 提取标题
                title = soup.find(['h1', 'h2', 'h3'])
                if title:
                    title_text = title.get_text().strip()
                else:
                    title_text = item.get_name()

                # 提取文本内容（前500字）
                text = soup.get_text().strip()
                preview = text[:500] if len(text) > 500 else text

                structure["chapters"].append({
                    "title": title_text,
                    "preview": preview,
                    "length": len(text)
                })

        return structure

    except Exception as e:
        print(f"提取失败: {e}")
        return None

if __name__ == "__main__":
    epub_path = r"d:\AI-Empowered IPTC Website\毛泽东思想和中国特色社会主义理论体系概论（2023）【数字版】.epub"

    print("正在提取epub文件结构...")
    structure = extract_epub_structure(epub_path)

    if structure:
        print(f"\n书名: {structure['title']}")
        print(f"作者: {structure['author']}")
        print(f"\n章节数: {len(structure['chapters'])}")
        print("\n章节列表:")
        print("=" * 80)

        for i, chapter in enumerate(structure['chapters'][:20], 1):  # 只显示前20章
            print(f"\n{i}. {chapter['title']}")
            print(f"   字数: {chapter['length']}")
            if chapter['preview']:
                print(f"   预览: {chapter['preview'][:100]}...")

        # 保存到JSON文件
        output_path = "epub_structure.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(structure, f, ensure_ascii=False, indent=2)

        print(f"\n\n完整结构已保存到: {output_path}")
    else:
        print("提取失败")
