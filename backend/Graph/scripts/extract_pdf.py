# -*- coding: utf-8 -*-
"""
从PDF文件中提取章节内容并生成JSON格式
"""
import sys
from pathlib import Path
import pdfplumber
import json
import re

def extract_pdf_content(pdf_path, book_name, book_id):
    """
    提取PDF文件的内容

    Args:
        pdf_path: PDF文件路径
        book_name: 书名
        book_id: 书籍ID

    Returns:
        包含章节内容的字典
    """
    try:
        chapters = []
        current_chapter = None

        print(f"正在打开PDF文件: {pdf_path}")
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"总页数: {total_pages}")

            for page_num, page in enumerate(pdf.pages, 1):
                if page_num % 10 == 0:
                    print(f"处理进度: {page_num}/{total_pages}")

                text = page.extract_text()
                if not text:
                    continue

                # 检测章节标题（简单的启发式规则）
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()

                    # 检测章节标题（如"第一章"、"第1章"等）
                    if re.match(r'^第[一二三四五六七八九十\d]+章', line):
                        # 保存上一章节
                        if current_chapter:
                            chapters.append(current_chapter)

                        # 开始新章节
                        current_chapter = {
                            "book_name": book_name,
                            "book_id": book_id,
                            "chapter_title": line,
                            "chapter_id": f"ch{len(chapters):02d}",
                            "content": "",
                            "start_page": page_num
                        }
                    elif current_chapter:
                        # 添加内容到当前章节
                        current_chapter["content"] += line + "\n"

        # 保存最后一章
        if current_chapter:
            chapters.append(current_chapter)

        return {
            "book_name": book_name,
            "book_id": book_id,
            "total_chapters": len(chapters),
            "chapters": chapters
        }

    except Exception as e:
        print(f"提取失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # PDF文件路径
    pdf_path = r"d:\AI-Empowered IPTC Website\文件\习近平新时代中国特色社会主义思想概论2023版.pdf"

    # 书籍信息
    book_name = "习近平新时代中国特色社会主义思想概论（2023）"
    book_id = "xi_thought_2023"

    print("="*80)
    print("开始提取PDF内容")
    print("="*80)

    # 提取内容
    result = extract_pdf_content(pdf_path, book_name, book_id)

    if result:
        print(f"\n提取完成！")
        print(f"书名: {result['book_name']}")
        print(f"章节数: {result['total_chapters']}")

        # 保存到JSON文件
        output_path = Path(__file__).parent.parent / "data" / f"{book_id}_chapters.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n内容已保存到: {output_path}")

        # 显示前3章预览
        print("\n前3章预览:")
        print("="*80)
        for chapter in result['chapters'][:3]:
            print(f"\n章节: {chapter['chapter_title']}")
            print(f"起始页: {chapter['start_page']}")
            print(f"内容长度: {len(chapter['content'])} 字符")
            print(f"内容预览: {chapter['content'][:200]}...")
    else:
        print("提取失败")

