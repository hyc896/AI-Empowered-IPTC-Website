# -*- coding: utf-8 -*-

"""
数据库迁移脚本：添加基本信息字段到 practice_submissions 表
运行方式：python -X utf8 migrations/add_basic_info_fields.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import engine
from sqlalchemy import text


def migrate():
    """添加 result_form, class_name_id, showcase_preference, instructor_name 字段"""
    columns_to_add = [
        ("result_form", "VARCHAR(100) COMMENT '成果形式（逗号分隔：文本图片,音频视频,实物,其他）'"),
        ("class_name_id", "VARCHAR(200) COMMENT '班级姓名学号'"),
        ("showcase_preference", "VARCHAR(20) DEFAULT 'original' COMMENT '公众号展示偏好: none/original/anonymous'"),
        ("instructor_name", "VARCHAR(100) COMMENT '任课教师姓名'"),
    ]

    with engine.connect() as conn:
        for col_name, col_def in columns_to_add:
            try:
                conn.execute(text(
                    f"ALTER TABLE practice_submissions ADD COLUMN {col_name} {col_def}"
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
