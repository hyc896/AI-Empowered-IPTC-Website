#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
更新消息源配置中的 ChromaDB collection 名称
将 personal_agent_ 前缀改为 mp_ 前缀
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.entities import MessageSource
from backend.database.connection import create_session


def update_collection_names():
    """更新所有消息源的 collection 名称"""

    with create_session() as db:
        # 查询所有消息源
        sources = db.query(MessageSource).all()

        print(f"找到 {len(sources)} 个消息源")
        print("-" * 80)

        updated_count = 0

        # 定义collection名称映射（基于mysql_table）
        table_to_collection = {
            'arxiv_messages': 'mp_arxiv',
            'kr36_messages': 'mp_kr36',
            'tonghuashun_messages': 'mp_tonghuashun'
        }

        for source in sources:
            config = source.config or {}
            old_collection = config.get('chroma_collection', '')
            mysql_table = config.get('mysql_table', '')

            # 确定新的collection名称
            new_collection = None

            if 'personal_agent_' in old_collection:
                # 如果包含 personal_agent_ 前缀，替换为 mp_
                new_collection = old_collection.replace('personal_agent_', 'mp_')
            elif mysql_table in table_to_collection:
                # 根据mysql_table映射到对应的collection
                new_collection = table_to_collection[mysql_table]

            if new_collection and new_collection != old_collection:
                print(f"消息源: {source.name} ({source.display_name})")
                print(f"  旧配置: {old_collection}")
                print(f"  新配置: {new_collection}")

                # 更新配置
                config['chroma_collection'] = new_collection
                source.config = config

                updated_count += 1
                print(f"  [OK] 已更新")
            else:
                print(f"消息源: {source.name} ({source.display_name})")
                print(f"  当前配置: {old_collection}")
                print(f"  [SKIP] 无需更新")

            print("-" * 80)

        # 提交更改
        if updated_count > 0:
            db.commit()
            print(f"\n[SUCCESS] 成功更新 {updated_count} 个消息源的配置")
        else:
            print("\n[INFO] 没有需要更新的配置")

        # 验证更新结果
        print("\n验证更新结果：")
        print("-" * 80)
        sources = db.query(MessageSource).all()
        for source in sources:
            config = source.config or {}
            collection = config.get('chroma_collection', 'N/A')
            print(f"{source.name:15} -> {collection}")


if __name__ == "__main__":
    try:
        update_collection_names()
    except Exception as e:
        print(f"\n[ERROR] 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
