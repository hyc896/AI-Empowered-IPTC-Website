#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查看案例内容"""
import pymysql
import json

# 连接数据库
conn = pymysql.connect(
    host='localhost',
    user='root',
    password='Hyc174513',
    database='message_platform',
    charset='utf8mb4'
)

cursor = conn.cursor()

# 查询最新的案例
cursor.execute("""
    SELECT id, title, content, related_knowledge_points, created_at
    FROM iptc_cases
    ORDER BY created_at DESC
    LIMIT 1
""")

result = cursor.fetchone()

if result:
    case_id, title, content, kp_json, created_at = result
    kp_list = json.loads(kp_json) if kp_json else []

    print("=" * 80)
    print(f"案例ID: {case_id}")
    print(f"标题: {title}")
    print(f"创建时间: {created_at}")
    print(f"关联知识点: {kp_list}")
    print("=" * 80)
    print("\n【案例内容】\n")
    print(content)
    print("\n" + "=" * 80)

    # 检查关键内容
    print("\n【内容检查】")
    if "理论分析" in content or "■ 理论分析" in content:
        print("✓ 包含理论分析部分")
    else:
        print("✗ 缺少理论分析部分")

    if "本案例主要适用于第" in content and "章" in content and "节" in content:
        print("✓ 包含精确的章节定位")
    else:
        print("✗ 缺少精确的章节定位")

    if "教学建议" in content or "■ 教学建议" in content:
        print("✓ 包含教学建议部分")
    else:
        print("✗ 缺少教学建议部分")

cursor.close()
conn.close()
