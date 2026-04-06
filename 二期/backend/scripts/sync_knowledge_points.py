# -*- coding: utf-8 -*-
"""
从一期 knowledge_points.json 同步知识点到二期 knowledge_points 表
"""

import json
import uuid
import sys
from pathlib import Path
from datetime import datetime

# 添加后端路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database.connection import SessionLocal, init_database
from database.entities import KnowledgePoint

# 书名到课程类别的映射
BOOK_CATEGORY_MAP = {
    "马克思主义基本原理（2023年版）": "马原",
    "习近平新时代中国特色社会主义思想概论（2023年版）": "习概",
    "思想道德与法治（2023年版）": "思修",
}


def sync_knowledge_points():
    # 读取一期知识点数据
    json_path = Path("D:/AI-Empowered IPTC Website/一期/backend/data/knowledge_points.json")
    if not json_path.exists():
        print(f"文件不存在: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        kp_list = json.load(f)

    print(f"读取到 {len(kp_list)} 个知识点")

    # 初始化数据库
    init_database()

    db = SessionLocal()
    try:
        # 清空现有知识点
        existing_count = db.query(KnowledgePoint).count()
        if existing_count > 0:
            db.query(KnowledgePoint).delete()
            db.commit()
            print(f"已清空 {existing_count} 条旧数据")

        # 导入知识点
        imported = 0
        for i, kp in enumerate(kp_list):
            book_name = kp.get("book_name", "")
            category = BOOK_CATEGORY_MAP.get(book_name, "其他")
            chapter = kp.get("chapter", "")
            name = kp.get("name", "")
            description = kp.get("theory_description", "")
            keywords = kp.get("typical_keywords", "")

            # 生成编码: 类别缩写_序号
            code = f"{category}_{i+1:03d}"

            knowledge_point = KnowledgePoint(
                id=str(uuid.uuid4()),
                code=code,
                name=name,
                category=category,
                chapter=chapter,
                description=description,
                keywords=keywords,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(knowledge_point)
            imported += 1

        db.commit()
        print(f"成功导入 {imported} 个知识点")

        # 统计
        for cat in ["马原", "习概", "思修"]:
            count = db.query(KnowledgePoint).filter(KnowledgePoint.category == cat).count()
            print(f"  {cat}: {count} 个")

    finally:
        db.close()


if __name__ == "__main__":
    sync_knowledge_points()
