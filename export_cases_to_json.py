# -*- coding: utf-8 -*-
"""
导出数据库中的案例为JSON文件
供前端直接读取使用
"""

import json
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from backend.database.connection import init_database, create_session
from backend.database.entities import IPTCCase
from datetime import datetime

def export_cases_to_json():
    """导出案例到JSON文件"""
    print("="*60)
    print("导出IPTC案例到JSON文件")
    print("="*60)

    # 初始化数据库
    print("\n1. 初始化数据库连接...")
    init_database()
    print("   [OK] 数据库连接成功")

    # 查询所有案例
    print("\n2. 查询数据库中的案例...")
    with create_session() as db:
        cases = db.query(IPTCCase).order_by(IPTCCase.created_at.desc()).all()
        print(f"   [OK] 找到 {len(cases)} 个案例")

        # 转换为JSON格式
        cases_data = []
        for case in cases:
            # 提取知识点名称数组
            knowledge_points = []
            if case.related_knowledge_points:
                for kp in case.related_knowledge_points:
                    if isinstance(kp, dict) and 'name' in kp:
                        knowledge_points.append(kp['name'])

            case_dict = {
                "id": case.id,
                "title": case.title,
                "content": case.content or "",
                "summary": case.summary or "",
                "source": "IPTC系统",
                "sourceUrl": case.source_url,
                "publishDate": case.published_at.isoformat() if case.published_at else case.created_at.isoformat(),
                "viewCount": 0,
                "knowledgePoints": knowledge_points,
                "createdAt": case.created_at.isoformat(),
                "updatedAt": case.updated_at.isoformat(),
            }
            cases_data.append(case_dict)

    # 保存到JSON文件
    print("\n3. 保存到JSON文件...")
    output_dir = os.path.join(os.path.dirname(__file__), "iptc-dashboard", "public")
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, "cases.json")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "code": 200,
            "message": "success",
            "data": {
                "items": cases_data,
                "total": len(cases_data),
                "page": 1,
                "pageSize": len(cases_data),
                "totalPages": 1
            },
            "exportTime": datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)

    print(f"   [OK] 已导出到: {output_file}")

    # 打印一些统计信息
    print("\n" + "="*60)
    print("导出完成！")
    print("="*60)
    print(f"案例总数: {len(cases_data)}")
    print(f"输出文件: {output_file}")
    print(f"文件大小: {os.path.getsize(output_file) / 1024:.2f} KB")

    # 打印前3个案例的标题
    if cases_data:
        print("\n前3个案例:")
        for i, case in enumerate(cases_data[:3], 1):
            print(f"  {i}. {case['title']}")
            print(f"     知识点: {', '.join(case['knowledgePoints'])}")

    print("\n" + "="*60)

if __name__ == "__main__":
    try:
        export_cases_to_json()
    except Exception as e:
        print(f"\n[ERROR] 导出失败: {e}")
        import traceback
        traceback.print_exc()
