# -*- coding: utf-8 -*-
"""
过滤知识点，只保留毛泽东思想教材的知识点
"""
import json
from pathlib import Path

data_dir = Path(__file__).parent.parent / "data"
kp_file = data_dir / "knowledge_points.json"

# 读取现有知识点
with open(kp_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"原始知识点数: {len(data)}")

# 过滤：只保留非习近平思想的知识点
filtered = [kp for kp in data if kp.get('book_id') != 'xi_thought_2023']

print(f"过滤后知识点数: {len(filtered)}")

# 保存
with open(kp_file, 'w', encoding='utf-8') as f:
    json.dump(filtered, f, ensure_ascii=False, indent=2)

print(f"已保存到: {kp_file}")
