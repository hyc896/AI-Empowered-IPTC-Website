# -*- coding: utf-8 -*-
"""
迁移 0002: 向 venues 表添加 case_id 和 relevance_reason 字段
运行方式（在 二期/ 目录下）：python -X utf8 backend/migrations/0002_add_venue_case_link.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import engine
from sqlalchemy import text


def migrate():
    columns = [
        ("case_id", "VARCHAR(36) COMMENT '来源案例ID（对应 iptc_main.iptc_cases.id）'"),
        ("relevance_reason", "TEXT COMMENT '与案例的关联理由（AI提取）'"),
    ]
    with engine.connect() as conn:
        for col_name, col_def in columns:
            try:
                conn.execute(text(f"ALTER TABLE venues ADD COLUMN {col_name} {col_def}"))
                conn.commit()
                print(f"✅ 已添加列: {col_name}")
            except Exception as e:
                if "duplicate column" in str(e).lower():
                    print(f"⏭️  列已存在，跳过: {col_name}")
                else:
                    print(f"❌ 添加列失败 {col_name}: {e}")
                    raise
    print("迁移 0002 完成")


if __name__ == "__main__":
    migrate()
