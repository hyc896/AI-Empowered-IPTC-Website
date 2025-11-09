# -*- coding: utf-8 -*-

"""
更新数据库配置为无前缀collection名称
使用flag_modified确保JSON字段更新生效
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.database.connection import create_session
from backend.database.entities import MessageSource
from sqlalchemy.orm.attributes import flag_modified

def update_config_no_prefix():
    """更新配置为无前缀名称"""

    print("\n" + "=" * 80)
    print("更新数据库配置 - 无前缀collection名称")
    print("=" * 80)

    # 映射关系：MySQL表名 → ChromaDB collection名称（无前缀）
    table_to_collection = {
        'mp_tonghuashun_messages': 'tonghuashun',
        'mp_kr36_messages': 'kr36',
        'mp_arxiv_messages': 'arxiv',
        # 兼容旧配置（没有mp_前缀的表名）
        'tonghuashun_messages': 'tonghuashun',
        'kr36_messages': 'kr36',
        'arxiv_messages': 'arxiv'
    }

    with create_session() as db:
        sources = db.query(MessageSource).filter(MessageSource.is_active == True).all()

        print(f"\n找到 {len(sources)} 个激活的消息源")
        print("-" * 80)

        updated_count = 0

        for source in sources:
            config = source.config or {}
            mysql_table = config.get('mysql_table', '')
            old_collection = config.get('chroma_collection', '')

            print(f"\n消息源: {source.display_name} ({source.name})")
            print(f"  MySQL表: {mysql_table}")
            print(f"  旧collection: {old_collection}")

            if mysql_table in table_to_collection:
                new_collection = table_to_collection[mysql_table]

                if new_collection != old_collection:
                    # 更新配置
                    config['chroma_collection'] = new_collection
                    source.config = config

                    # 关键：显式标记字段已修改
                    flag_modified(source, 'config')
                    db.add(source)

                    print(f"  → 新collection: {new_collection} [已更新]")
                    updated_count += 1
                else:
                    print(f"  → 保持不变: {new_collection} [已是正确配置]")
            else:
                print(f"  [警告] 未知的mysql_table: {mysql_table}")

        # 提交所有修改
        if updated_count > 0:
            db.commit()
            print("\n" + "-" * 80)
            print(f"[提交] 已更新 {updated_count} 个消息源的配置")
        else:
            print("\n" + "-" * 80)
            print("[跳过] 所有配置已是正确值，无需更新")

    # 验证更新结果
    print("\n" + "=" * 80)
    print("验证更新结果")
    print("=" * 80)

    with create_session() as db:
        sources = db.query(MessageSource).filter(MessageSource.is_active == True).all()

        print(f"\n当前配置:")
        print("-" * 80)

        all_correct = True
        for source in sources:
            config = source.config or {}
            collection_name = config.get('chroma_collection', '[未配置]')
            mysql_table = config.get('mysql_table', '[未配置]')

            # 检查是否是无前缀名称
            is_correct = collection_name in ['tonghuashun', 'kr36', 'arxiv']
            status = "[OK]" if is_correct else "[ERROR]"

            print(f"\n{source.display_name:20s}")
            print(f"  MySQL表: {mysql_table}")
            print(f"  Collection: {collection_name} {status}")

            if not is_correct:
                all_correct = False

    print("\n" + "=" * 80)
    if all_correct:
        print("[成功] 所有配置已更新为无前缀名称")
    else:
        print("[警告] 部分配置仍不正确，请检查")
    print("=" * 80 + "\n")

if __name__ == '__main__':
    update_config_no_prefix()
