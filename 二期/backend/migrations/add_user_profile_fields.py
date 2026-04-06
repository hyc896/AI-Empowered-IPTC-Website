# -*- coding: utf-8 -*-

"""
数据库迁移脚本：添加专业和兴趣字段到 users 表
运行方式：python -X utf8 migrations/add_user_profile_fields.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import engine
from sqlalchemy import text


def migrate():
    """添加 major, interests 字段到 users 表"""
    columns_to_add = [
        ("major", "VARCHAR(100) COMMENT '专业'"),
        ("interests", "VARCHAR(500) COMMENT '兴趣爱好/特长'"),
    ]

    with engine.connect() as conn:
        for col_name, col_def in columns_to_add:
            try:
                conn.execute(text(
                    f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"
                ))
                conn.commit()
                print(f"✅ 已添加列: {col_name}")
            except Exception as e:
                if "Duplicate column" in str(e) or "duplicate column" in str(e).lower():
                    print(f"⏭️ 列已存在，跳过: {col_name}")
                else:
                    print(f"❌ 添加列失败 {col_name}: {e}")

    print("\n迁移完成！")


if __name__ == "__main__":
    migrate()
