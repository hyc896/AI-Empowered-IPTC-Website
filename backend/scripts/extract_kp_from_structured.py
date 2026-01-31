# -*- coding: utf-8 -*-
"""
从结构化内容中提取知识点并追加到现有文件
"""
import json
import sys
import asyncio
from pathlib import Path

# 添加backend目录到path
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

from scripts.extract_knowledge_points import (
    initialize_llm_manager,
    extract_knowledge_points_from_chapter
)


async def extract_from_structured_content():
    """
    从结构化内容中提取知识点
    """
    data_dir = Path(__file__).parent.parent / "data"
    structured_file = data_dir / "xi_thought_2023_structured.json"
    kp_file = data_dir / "knowledge_points.json"

    print("="*80)
    print("从结构化内容提取知识点")
    print("="*80)

    # 读取结构化内容
    print(f"\n正在读取结构化内容: {structured_file}")
    with open(structured_file, 'r', encoding='utf-8') as f:
        structured_data = json.load(f)

    book_name = structured_data.get('book_name')
    book_id = structured_data.get('book_id')
    chapters = structured_data.get('chapters', [])

    print(f"书名: {book_name}")
    print(f"书籍ID: {book_id}")
    print(f"章节数: {len(chapters)}")

    # 读取现有知识点
    print(f"\n正在读取现有知识点: {kp_file}")
    with open(kp_file, 'r', encoding='utf-8') as f:
        existing_kps = json.load(f)

    print(f"现有知识点数: {len(existing_kps)}")

    # 提取新知识点
    new_kps = []
    total_chapters = len(chapters)

    print(f"\n开始提取 {total_chapters} 个章节的知识点...")

    for i, chapter in enumerate(chapters, 1):
        chapter_num = chapter.get('chapter_num')
        chapter_title = chapter.get('chapter_title')
        chapter_id = chapter.get('chapter_id')

        print(f"\n[{i}/{total_chapters}] 第{chapter_num}章: {chapter_title}")

        sections = chapter.get('sections', [])
        if not sections:
            print(f"  [警告] 章节没有节内容，跳过")
            continue

        print(f"  共 {len(sections)} 个节")

        # 按节提取知识点
        for j, section in enumerate(sections, 1):
            section_num = section.get('section_num')
            section_title = section.get('section_title')
            section_id = section.get('section_id')

            print(f"\n  [{j}/{len(sections)}] 第{section_num}节: {section_title}")

            # 收集节的所有文本内容
            section_texts = []

            # 添加节级别的内容
            if section.get('content'):
                section_texts.append(section['content'])

            # 添加所有小节的内容
            for subsection in section.get('subsections', []):
                if subsection.get('content'):
                    section_texts.append(subsection['content'])

            # 合并文本
            section_text = '\n\n'.join(section_texts)

            if not section_text.strip():
                print(f"    [警告] 节没有文本内容，跳过")
                continue

            print(f"    文本长度: {len(section_text)} 字符")

            try:
                # 提取知识点
                kps = await extract_knowledge_points_from_chapter(
                    chapter_id=chapter_id,
                    chapter_name=f"第{chapter_num}章 {chapter_title}",
                    chapter_text=section_text,
                    book_name=book_name,
                    book_id=book_id,
                    section_id=section_id,
                    section_name=f"第{section_num}节 {section_title}"
                )

                new_kps.extend(kps)
                print(f"    [成功] 提取到 {len(kps)} 个知识点")

                # 延迟避免API限流
                await asyncio.sleep(2)

            except Exception as e:
                print(f"    [错误] 提取失败: {e}")
                continue

    # 合并并保存
    if new_kps:
        all_kps = existing_kps + new_kps
        with open(kp_file, 'w', encoding='utf-8') as f:
            json.dump(all_kps, f, ensure_ascii=False, indent=2)

        print(f"\n[完成] 新提取 {len(new_kps)} 个知识点")
        print(f"[完成] 总计 {len(all_kps)} 个知识点")
        print(f"[保存] 保存到: {kp_file}")
    else:
        print("\n[完成] 未提取到新知识点")


if __name__ == "__main__":
    # 初始化LLM管理器
    initialize_llm_manager()

    # 运行提取任务
    asyncio.run(extract_from_structured_content())
