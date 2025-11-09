# -*- coding: utf-8 -*-

"""
更新message_platform数据库中的collection名称配置
将所有消息源的chroma_collection改为mp_前缀
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.database.connection import create_session
from backend.database.entities import MessageSource

def update_collection_names():
    """更新所有消息源的chroma_collection配置为mp_前缀"""

    # 表名到collection名称的映射
    table_to_collection = {
        'arxiv_messages': 'mp_arxiv',
        'kr36_messages': 'mp_kr36',
        'tonghuashun_messages': 'mp_tonghuashun'
    }

    with create_session() as db:
        sources = db.query(MessageSource).filter(MessageSource.is_active == True).all()

        print(f"\n找到 {len(sources)} 个激活的消息源")
        print("=" * 80)

        for source in sources:
            config = source.config or {}
            mysql_table = config.get('mysql_table', '')
            old_collection = config.get('chroma_collection', '')

            if mysql_table in table_to_collection:
                new_collection = table_to_collection[mysql_table]

                if new_collection != old_collection:
                    config['chroma_collection'] = new_collection
                    source.config = config

                    # 标记为修改
                    db.add(source)

                    print(f"[OK] {source.display_name}")
                    print(f"     {old_collection} -> {new_collection}")
                else:
                    print(f"[SKIP] {source.display_name} - 已经是正确配置: {new_collection}")
            else:
                print(f"[WARN] {source.display_name} - 未知的mysql_table: {mysql_table}")

        # 提交所有修改
        db.commit()
        print("\n" + "=" * 80)
        print("[INFO] 数据库配置更新完成！")

        # 验证更新结果
        print("\n验证更新结果:")
        print("=" * 80)
        sources = db.query(MessageSource).filter(MessageSource.is_active == True).all()
        for source in sources:
            config = source.config or {}
            collection_name = config.get('chroma_collection', 'N/A')
            print(f"{source.display_name:20s} -> {collection_name}")

if __name__ == '__main__':
    update_collection_names()
