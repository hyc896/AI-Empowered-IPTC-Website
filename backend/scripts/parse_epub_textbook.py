# -*- coding: utf-8 -*-
"""
从EPUB教材中提取章节文本
"""
import json
import sys
import os
from pathlib import Path

# 设置控制台输出编码为UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
except ImportError:
    print("正在安装必要的依赖...")
    os.system("pip install ebooklib beautifulsoup4 -i https://pypi.tuna.tsinghua.edu.cn/simple")
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup


def extract_chapters_from_epub(epub_path: str) -> list:
    """
    从EPUB中提取章节文本

    Args:
        epub_path: EPUB文件路径

    Returns:
        章节列表，格式: [{"chapter_id": "ch01", "chapter_name": "...", "sections": [...]}]
    """
    print(f"正在读取EPUB文件: {epub_path}")

    try:
        book = epub.read_epub(epub_path)
    except Exception as e:
        print(f"[错误] 读取EPUB失败: {e}")
        return []

    chapters = []
    chapter_counter = 0
    section_counter = 0

    print("正在提取章节内容...")

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            try:
                content = item.get_content()
                soup = BeautifulSoup(content, 'html.parser')

                # 提取文本内容
                text = soup.get_text(separator='\n', strip=True)

                # 过滤空白内容
                if not text or len(text) < 100:
                    continue

                # 识别章节标题
                title_tag = soup.find(['h1', 'h2', 'h3'])
                if title_tag:
                    title = title_tag.get_text(strip=True)
                else:
                    # 尝试从第一行提取标题
                    first_line = text.split('\n')[0]
                    if len(first_line) < 100 and ('第' in first_line or '章' in first_line):
                        title = first_line
                    else:
                        title = f"未命名章节 {section_counter + 1}"

                # 判断是否为章节（包含"第X章"）或节（包含"第X节"）
                is_chapter = '第' in title and '章' in title

                if is_chapter:
                    # 新章节
                    chapter_counter += 1
                    section_counter = 0

                    chapters.append({
                        "chapter_id": f"ch{chapter_counter:02d}",
                        "chapter_name": title,
                        "sections": []
                    })

                    print(f"  [章节] 提取章节: {title}")

                else:
                    # 节或内容段落
                    if not chapters:
                        # 如果还没有章节，创建一个默认章节
                        chapter_counter += 1
                        chapters.append({
                            "chapter_id": f"ch{chapter_counter:02d}",
                            "chapter_name": "导言",
                            "sections": []
                        })

                    section_counter += 1

                    # 保留完整文本（不再限制长度）
                    chapters[-1]["sections"].append({
                        "section_id": f"ch{chapter_counter:02d}_s{section_counter:02d}",
                        "section_name": title,
                        "text": text
                    })

                    print(f"    → 提取节: {title} (文本长度: {len(text)} 字)")

            except Exception as e:
                print(f"  [警告] 处理章节时出错: {e}")
                continue

    print(f"\n[完成] 提取完成！共提取 {len(chapters)} 个章节")

    # 统计节数
    total_sections = sum(len(ch["sections"]) for ch in chapters)
    print(f"[统计] 总共包含 {total_sections} 个节")

    return chapters


def main():
    """主函数"""
    # EPUB文件路径
    epub_path = r"D:\AI-Empowered IPTC Website\毛泽东思想和中国特色社会主义理论体系概论（2023）【数字版】.epub"

    # 输出文件路径
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "textbook_chapters.json"

    # 提取章节
    chapters = extract_chapters_from_epub(epub_path)

    if not chapters:
        print("[错误] 未能提取到任何章节")
        sys.exit(1)

    # 保存到JSON文件
    print(f"\n正在保存到: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chapters, f, ensure_ascii=False, indent=2)

    print(f"[成功] 成功保存到: {output_file}")

    # 打印示例
    print("\n" + "="*60)
    print("示例章节结构:")
    print("="*60)
    if chapters:
        print(json.dumps(chapters[0], ensure_ascii=False, indent=2)[:500])
        print("...")


if __name__ == "__main__":
    main()
