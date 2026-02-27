#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""统计知识点和消息数量"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.storage.chromadb_storage import ChromaDBStorage
from backend.config.config_manager import ConfigManager
from backend.database.connection import create_session
from sqlalchemy import text

def main():
    # 1. 统计知识点数量（ChromaDB）
    print("=" * 60)
    print("统计知识点数量（ChromaDB）")
    print("=" * 60)

    try:
        config_manager = ConfigManager()
        config_manager.load_config('config.yaml')
        config = config_manager.get_config()
        chroma_config = config.get('database', {}).get('chromadb', {})

        storage = ChromaDBStorage()
        storage.initialize(chroma_config)

        kp_count = storage.get_collection_count('iptc_knowledge_points')
        print(f"知识点数量: {kp_count}")
    except Exception as e:
        print(f"统计知识点失败: {e}")

    print()

    # 2. 统计消息数量（MySQL）
    print("=" * 60)
    print("统计消息数量（MySQL）")
    print("=" * 60)

    try:
        with create_session() as session:
            # 获取所有消息表
            result = session.execute(text("SHOW TABLES LIKE 'mp_%_messages'"))
            tables = [row[0] for row in result]

            total_messages = 0
            print(f"\n找到 {len(tables)} 个消息表：\n")

            for table in sorted(tables):
                count_result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = count_result.scalar()
                total_messages += count
                if count > 0:
                    print(f"  {table}: {count:,} 条")

            print(f"\n{'=' * 60}")
            print(f"消息总数: {total_messages:,} 条")
            print(f"{'=' * 60}")
    except Exception as e:
        print(f"统计消息失败: {e}")

if __name__ == "__main__":
    main()
