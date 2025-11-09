# -*- coding: utf-8 -*-

"""
清理ChromaDB中的孤立向量数据
孤立数据定义：ChromaDB中存在但MySQL中不存在的向量

策略：
1. 对比ChromaDB与MySQL的ID差集
2. 删除ChromaDB中MySQL不存在的向量
3. 确保ChromaDB与MySQL完全对齐
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.database.connection import create_session
from backend.database.entities import TongHuaShunMessage, Kr36Message, ArxivMessage, MessageSource
import chromadb

def clean_orphan_data():
    """清理ChromaDB孤立数据"""

    print("\n" + "=" * 80)
    print("清理ChromaDB孤立向量数据")
    print("=" * 80)

    # 连接数据库
    chromadb_path = "./data/chromadb_mp"
    print(f"\nChromaDB路径: {chromadb_path}")

    try:
        client = chromadb.PersistentClient(path=chromadb_path)
        print("[连接] ChromaDB连接成功")
    except Exception as e:
        print(f"[错误] ChromaDB连接失败: {e}")
        return 1

    # 获取消息源配置
    with create_session() as db:
        sources = db.query(MessageSource).filter(MessageSource.is_active == True).all()

        if not sources:
            print("[错误] 未找到激活的消息源")
            return 1

        print(f"[配置] 找到 {len(sources)} 个激活的消息源")

    # 对每个消息源进行清理
    total_deleted = 0

    for source in sources:
        source_name = source.display_name or source.name
        config = source.config or {}
        mysql_table = config.get('mysql_table', '')
        chroma_collection = config.get('chroma_collection', '')

        print(f"\n{'='*80}")
        print(f"处理消息源: {source_name}")
        print(f"MySQL表: {mysql_table}")
        print(f"ChromaDB Collection: {chroma_collection}")
        print(f"{'='*80}")

        # 确定表模型和ID字段
        if 'tonghuashun' in mysql_table:
            model = TongHuaShunMessage
            id_field = 'seq'
        elif 'kr36' in mysql_table:
            model = Kr36Message
            id_field = 'item_id'
        elif 'arxiv' in mysql_table:
            model = ArxivMessage
            id_field = 'arxiv_id'
        else:
            print(f"[跳过] 未知的表类型: {mysql_table}")
            continue

        try:
            # 1. 获取MySQL中的所有ID
            with create_session() as db:
                id_column = getattr(model, id_field)
                results = db.query(id_column).all()
                mysql_ids = set(str(row[0]) for row in results if row[0] is not None)

            print(f"\n[MySQL] 共有 {len(mysql_ids)} 条记录")

            # 2. 获取ChromaDB中的所有ID
            collection = client.get_collection(name=chroma_collection)
            chroma_count = collection.count()
            print(f"[ChromaDB] 共有 {chroma_count} 条向量")

            if chroma_count == 0:
                print("[跳过] ChromaDB为空")
                continue

            # 批量获取所有ChromaDB中的ID
            batch_size = 1000
            all_chroma_ids = []

            for offset in range(0, chroma_count, batch_size):
                limit = min(batch_size, chroma_count - offset)
                data = collection.get(
                    limit=limit,
                    offset=offset,
                    include=[]
                )
                all_chroma_ids.extend(data.get('ids', []))

            chroma_ids = set(all_chroma_ids)
            print(f"[ChromaDB] 唯一ID数量: {len(chroma_ids)}")

            # 3. 计算孤立数据（ChromaDB有但MySQL没有）
            orphan_ids = chroma_ids - mysql_ids

            if not orphan_ids:
                print(f"[完整] 无孤立数据，MySQL与ChromaDB完全对齐")
                continue

            print(f"\n[发现] 孤立向量数据: {len(orphan_ids)} 条")
            print(f"[详情] 前10个孤立ID: {list(orphan_ids)[:10]}")

            # 4. 询问是否删除
            print(f"\n准备删除 {len(orphan_ids)} 条孤立向量...")
            response = input("是否继续？(yes/no): ").strip().lower()

            if response != 'yes':
                print("[取消] 跳过删除")
                continue

            # 5. 删除孤立数据
            print(f"[删除] 正在删除孤立数据...")

            # ChromaDB的delete()方法
            orphan_list = list(orphan_ids)
            batch_size_delete = 1000

            deleted_count = 0
            for i in range(0, len(orphan_list), batch_size_delete):
                batch_ids = orphan_list[i:i + batch_size_delete]
                try:
                    collection.delete(ids=batch_ids)
                    deleted_count += len(batch_ids)
                    print(f"[进度] 已删除 {deleted_count}/{len(orphan_list)} 条")
                except Exception as e:
                    print(f"[警告] 批次删除失败: {e}")
                    continue

            # 6. 验证删除结果
            final_count = collection.count()
            print(f"\n[验证] 删除后ChromaDB记录数: {final_count}")
            print(f"[验证] MySQL记录数: {len(mysql_ids)}")

            if final_count == len(mysql_ids):
                print(f"[成功] ChromaDB与MySQL已对齐！")
            else:
                print(f"[警告] 仍有差异: {abs(final_count - len(mysql_ids))} 条")

            total_deleted += deleted_count

        except Exception as e:
            print(f"[错误] 处理失败: {e}")
            import traceback
            traceback.print_exc()
            continue

    # 总结
    print("\n" + "=" * 80)
    print("清理完成")
    print("=" * 80)
    print(f"\n总共删除孤立向量: {total_deleted} 条")

    return 0

if __name__ == '__main__':
    exit_code = clean_orphan_data()
    sys.exit(exit_code)
