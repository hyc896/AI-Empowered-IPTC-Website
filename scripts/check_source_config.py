#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查消息源配置
"""

import sys
import os
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.entities import MessageSource
from backend.database.connection import create_session


def check_source_config():
    """检查所有消息源的配置"""

    with create_session() as db:
        sources = db.query(MessageSource).all()

        print(f"找到 {len(sources)} 个消息源")
        print("=" * 80)

        for source in sources:
            print(f"\n消息源: {source.name} ({source.display_name})")
            print(f"ID: {source.id}")
            print(f"Category: {source.category}")
            print(f"Active: {source.is_active}")
            print(f"Config:")
            if source.config:
                print(json.dumps(source.config, indent=2, ensure_ascii=False))
            else:
                print("  (empty)")
            print("=" * 80)


if __name__ == "__main__":
    try:
        check_source_config()
    except Exception as e:
        print(f"\n[ERROR] 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
