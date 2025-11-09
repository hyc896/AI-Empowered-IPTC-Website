# -*- coding: utf-8 -*-

"""
检查ChromaDB中的脏数据
检测：
1. 是否有旧的带前缀collection（personal_agent_*, mp_*）
2. 当前collection中是否有重复ID
3. 统计count()与实际唯一ID数量的差异
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import chromadb
from collections import Counter

def check_dirty_data():
    """检查ChromaDB脏数据"""

    print("\n" + "=" * 80)
    print("ChromaDB 脏数据检查")
    print("=" * 80)

    # 连接ChromaDB
    chromadb_path = "./data/chromadb_mp"
    print(f"\n数据库路径: {chromadb_path}")

    try:
        client = chromadb.PersistentClient(path=chromadb_path)
        print("[成功] ChromaDB连接成功")
    except Exception as e:
        print(f"[错误] ChromaDB连接失败: {e}")
        return 1

    # 1. 列出所有collection
    print("\n" + "-" * 80)
    print("步骤1: 列出所有collection")
    print("-" * 80)

    try:
        collections = client.list_collections()
        print(f"\n找到 {len(collections)} 个collection:")

        for coll in collections:
            count = coll.count()
            print(f"  - {coll.name}: {count} 条")

            # 标记可疑的旧collection
            if any(prefix in coll.name for prefix in ['personal_agent_', 'mp_']):
                print(f"    [警告] 疑似旧collection，包含前缀")

    except Exception as e:
        print(f"[错误] 列出collection失败: {e}")
        return 1

    # 2. 检查目标collection的重复ID
    print("\n" + "-" * 80)
    print("步骤2: 检查目标collection的数据完整性")
    print("-" * 80)

    target_collections = ['tonghuashun', 'kr36', 'arxiv']

    for coll_name in target_collections:
        print(f"\n检查: {coll_name}")
        print("-" * 40)

        try:
            collection = client.get_collection(name=coll_name)

            # 使用count()统计
            total_count = collection.count()
            print(f"  count() 方法: {total_count} 条")

            # 使用get()获取所有数据，检查实际唯一ID数量
            if total_count > 0:
                # 分批获取所有数据
                batch_size = 1000
                all_ids = []

                for offset in range(0, total_count, batch_size):
                    limit = min(batch_size, total_count - offset)
                    data = collection.get(
                        limit=limit,
                        offset=offset,
                        include=[]  # 只获取ID，不获取embeddings和documents
                    )
                    all_ids.extend(data.get('ids', []))

                unique_ids = set(all_ids)
                print(f"  get() 方法实际获取: {len(all_ids)} 条")
                print(f"  唯一ID数量: {len(unique_ids)} 条")

                # 检查是否有重复
                if len(all_ids) != len(unique_ids):
                    duplicate_count = len(all_ids) - len(unique_ids)
                    print(f"  [警告] 发现重复数据: {duplicate_count} 条")

                    # 统计重复的ID
                    id_counter = Counter(all_ids)
                    duplicates = {id_: count for id_, count in id_counter.items() if count > 1}

                    if duplicates:
                        print(f"  [详情] 重复的ID数量: {len(duplicates)} 个")
                        print(f"  [详情] 前5个重复ID示例:")
                        for i, (id_, count) in enumerate(list(duplicates.items())[:5]):
                            print(f"    - ID '{id_}' 重复 {count} 次")
                else:
                    print(f"  [正常] 无重复数据")

                # 检查差异
                if total_count != len(unique_ids):
                    diff = total_count - len(unique_ids)
                    print(f"  [差异] count()与唯一ID差: {diff} 条")
                else:
                    print(f"  [正常] count()与唯一ID一致")
            else:
                print(f"  [信息] collection为空")

        except Exception as e:
            print(f"  [错误] 检查失败: {e}")
            import traceback
            traceback.print_exc()

    # 3. 总结
    print("\n" + "=" * 80)
    print("检查完成")
    print("=" * 80)

    return 0

if __name__ == '__main__':
    exit_code = check_dirty_data()
    sys.exit(exit_code)
