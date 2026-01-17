# -*- coding: utf-8 -*-
"""
从已提取的文本中重新切分章节
"""
import json
import re
from pathlib import Path


def split_chapters_from_text(text: str) -> list:
    """
    从提取的文本中识别并切分章节

    Args:
        text: 提取的完整文本

    Returns:
        章节列表
    """
    chapters = []

    # 正则模式：识别章节标题
    # 格式1: "导论" 或 "导 论"
    # 格式2: "第一章"、"第二章" 等
    # 格式3: "第1章"、"第2章" 等
    # 格式4: "结束语"
    chapter_pattern = r'(导\s*论|第[一二三四五六七八九十]+章|第\d+章|结束语)\s*([^\n]{0,50})'

    # 查找所有章节标题
    matches = list(re.finditer(chapter_pattern, text))

    if not matches:
        print("[警告] 未找到章节标题")
        return []

    print(f"[发现] 找到 {len(matches)} 个章节标题")

    # 提取每个章节的内容
    for i, match in enumerate(matches):
        chapter_num_text = match.group(1)  # "导论" 或 "第X章"
        chapter_title_text = match.group(2).strip()  # 章节标题

        # 完整标题
        full_title = f"{chapter_num_text} {chapter_title_text}"

        # 提取章节内容（从当前标题到下一个标题之间）
        start_pos = match.start()
        if i < len(matches) - 1:
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(text)

        chapter_content = text[start_pos:end_pos]

        # 生成chapter_id
        if '导论' in chapter_num_text or '导 论' in chapter_num_text:
            chapter_id = "ch00"
        elif '结束语' in chapter_num_text:
            chapter_id = "ch99"
        else:
            # 提取章节编号
            num_match = re.search(r'第([一二三四五六七八九十\d]+)章', chapter_num_text)
            if num_match:
                num_str = num_match.group(1)
                # 转换中文数字或阿拉伯数字
                num = convert_chinese_number(num_str)
                chapter_id = f"ch{num:02d}"
            else:
                chapter_id = f"ch{i+1:02d}"

        chapters.append({
            "chapter_id": chapter_id,
            "chapter_name": full_title,
            "sections": [
                {
                    "section_id": f"{chapter_id}_s01",
                    "section_name": full_title,
                    "text": chapter_content.strip()
                }
            ]
        })

        print(f"  [提取] {full_title} (文本长度: {len(chapter_content)} 字)")

    return chapters


def convert_chinese_number(chinese_num: str) -> int:
    """
    转换中文数字为阿拉伯数字

    Args:
        chinese_num: 中文数字字符串（如"一"、"二十"）

    Returns:
        阿拉伯数字
    """
    # 如果已经是阿拉伯数字，直接返回
    if chinese_num.isdigit():
        return int(chinese_num)

    # 中文数字映射
    chinese_map = {
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
    }

    # 简单处理：一到十
    if chinese_num in chinese_map:
        return chinese_map[chinese_num]

    # 处理十几、二十等
    if '十' in chinese_num:
        if chinese_num == '十':
            return 10
        elif chinese_num.startswith('十'):
            # 十一、十二...
            return 10 + chinese_map.get(chinese_num[1], 0)
        else:
            # 二十、三十...
            tens = chinese_map.get(chinese_num[0], 0) * 10
            if len(chinese_num) > 2:
                ones = chinese_map.get(chinese_num[2], 0)
            else:
                ones = 0
            return tens + ones

    return 1


def main():
    """主函数"""
    # 读取已提取的JSON
    data_dir = Path(__file__).parent.parent / "data"
    input_file = data_dir / "textbook_chapters.json"

    print(f"正在读取: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    # 提取文本
    if raw_data and len(raw_data) > 0 and 'sections' in raw_data[0]:
        text = raw_data[0]['sections'][0]['text']
        print(f"原始文本长度: {len(text)} 字")
    else:
        print("[错误] 无法从JSON中提取文本")
        return

    # 切分章节
    chapters = split_chapters_from_text(text)

    if not chapters:
        print("[错误] 未能切分出章节")
        return

    # 保存
    output_file = data_dir / "textbook_chapters.json"
    print(f"\n正在保存到: {output_file}")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chapters, f, ensure_ascii=False, indent=2)

    print(f"[完成] 成功切分 {len(chapters)} 个章节")

    # 打印示例
    print("\n" + "="*60)
    print("示例章节:")
    print("="*60)
    for ch in chapters[:3]:
        print(f"- {ch['chapter_name']} ({len(ch['sections'][0]['text'])} 字)")


if __name__ == "__main__":
    main()
