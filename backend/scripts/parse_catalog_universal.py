# -*- coding: utf-8 -*-
"""
通用目录解析脚本 - 支持多本教材
"""
import sys
import json
import re
from pathlib import Path

backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

class CatalogParser:
    def __init__(self, catalog_file, book_name, book_id):
        self.catalog_file = catalog_file
        self.book_name = book_name
        self.book_id = book_id
        self.knowledge_points = []

        # 中文数字映射
        self.chinese_nums = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
        }

    def parse(self):
        """解析目录文件"""
        with open(self.catalog_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        current_chapter = None
        current_chapter_id = 0
        current_section = None
        current_section_id = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 匹配章节: 第X章 或 导论 或 绪论
            chapter_match = re.match(r'^\d+\.\s*(第([一二三四五六七八九十]+)章\s+(.+?)/\d+|导\s*论\s+(.+?)/\d+|绪\s*论\s+(.+?)/\d+)', line)
            if chapter_match:
                if chapter_match.group(2):  # 第X章
                    chapter_num = self.chinese_nums.get(chapter_match.group(2), 0)
                    chapter_title = chapter_match.group(3).strip()
                    current_chapter = f"第{chapter_match.group(2)}章 {chapter_title}"
                    current_chapter_id = chapter_num
                elif chapter_match.group(4):  # 导论
                    current_chapter = f"导论 {chapter_match.group(4).strip()}"
                    current_chapter_id = 0
                elif chapter_match.group(5):  # 绪论
                    current_chapter = f"绪论 {chapter_match.group(5).strip()}"
                    current_chapter_id = 0
                current_section = None
                current_section_id = 0
                continue

            # 匹配节: 第X节
            section_match = re.match(r'^\d+\.\s*第([一二三四五六七八九十]+)节\s+(.+?)/\d+', line)
            if section_match:
                section_num = self.chinese_nums.get(section_match.group(1), 0)
                section_title = section_match.group(2).strip()
                current_section = f"第{section_match.group(1)}节 {section_title}"
                current_section_id = section_num
                continue

            # 匹配部: 一、二、三、四、五、六
            part_match = re.match(r'^\d+\.\s*([一二三四五六七八九十]+)、(.+?)/\d+', line)
            if part_match and current_chapter:
                part_num_chinese = part_match.group(1)
                part_num = self.chinese_nums.get(part_num_chinese, 0)
                part_title = part_match.group(2).strip()

                # 创建知识点
                kp = {
                    "name": part_title,
                    "book_name": self.book_name,
                    "book_id": self.book_id,
                    "chapter": current_chapter,
                    "chapter_id": current_chapter_id,
                    "part": f"{part_num_chinese}、{part_title}",
                    "part_num": part_num
                }

                # 如果有节,添加节信息
                if current_section:
                    kp["section"] = current_section
                    kp["section_id"] = current_section_id
                else:
                    # 导论/绪论没有节,直接在章下
                    kp["section"] = current_chapter
                    kp["section_id"] = 0

                self.knowledge_points.append(kp)

        return self.knowledge_points

    def save(self, output_file):
        """保存解析结果"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.knowledge_points, f, ensure_ascii=False, indent=2)

        print(f"成功解析 {len(self.knowledge_points)} 个知识点")
        print(f"已保存到: {output_file}")

def main():
    # 解析习近平思想概论
    print("=" * 60)
    print("解析习近平思想概论目录")
    print("=" * 60)

    xi_parser = CatalogParser(
        catalog_file=backend_dir / "data" / "xi_catalog.txt",
        book_name="习近平新时代中国特色社会主义思想概论（2023年版）",
        book_id="xi_thought_2023"
    )
    xi_kps = xi_parser.parse()
    xi_parser.save(backend_dir / "data" / "xi_kp_structure.json")

    print("\n前5个知识点:")
    for i, kp in enumerate(xi_kps[:5], 1):
        print(f"{i}. {kp['name']}")
        print(f"   章节: {kp['chapter']}")
        if kp.get('section') != kp['chapter']:
            print(f"   节: {kp['section']}")

    # 解析思想道德与法治
    print("\n" + "=" * 60)
    print("解析思想道德与法治目录")
    print("=" * 60)

    morality_parser = CatalogParser(
        catalog_file=backend_dir / "data" / "morality_catalog.txt",
        book_name="思想道德与法治（2023年版）",
        book_id="morality_law_2023"
    )
    morality_kps = morality_parser.parse()
    morality_parser.save(backend_dir / "data" / "morality_kp_structure.json")

    print("\n前5个知识点:")
    for i, kp in enumerate(morality_kps[:5], 1):
        print(f"{i}. {kp['name']}")
        print(f"   章节: {kp['chapter']}")
        if kp.get('section') != kp['chapter']:
            print(f"   节: {kp['section']}")

    print("\n" + "=" * 60)
    print(f"总计: {len(xi_kps) + len(morality_kps)} 个知识点")
    print("=" * 60)

if __name__ == "__main__":
    main()
