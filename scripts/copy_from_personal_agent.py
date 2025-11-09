# -*- coding: utf-8 -*-

"""
从personal_agent的ChromaDB复制向量数据到message_platform
只复制数据，不删除源数据，确保安全
"""

import chromadb
import sys
from typing import Dict, List

def copy_collection(
    source_client: chromadb.Client,
    target_client: chromadb.Client,
    source_name: str,
    target_name: str
) -> bool:
    """
    复制collection数据

    Args:
        source_client: 源ChromaDB客户端
        target_client: 目标ChromaDB客户端
        source_name: 源collection名称
        target_name: 目标collection名称

    Returns:
        是否成功
    """
    try:
        # 获取源collection
        source_collection = source_client.get_collection(name=source_name)
        source_count = source_collection.count()

        print(f"\n{'='*80}")
        print(f"正在复制: {source_name} → {target_name}")
        print(f"源数据量: {source_count} 条")
        print(f"{'='*80}")

        if source_count == 0:
            print("[跳过] 源collection为空")
            return True

        # 创建或获取目标collection
        try:
            target_collection = target_client.get_collection(name=target_name)
            print(f"[信息] 目标collection已存在，将追加数据")
        except:
            target_collection = target_client.create_collection(
                name=target_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"[创建] 目标collection已创建")

        # 分批复制数据（每批1000条，避免内存溢出）
        batch_size = 1000
        total_copied = 0

        for offset in range(0, source_count, batch_size):
            limit = min(batch_size, source_count - offset)

            # 从源collection获取数据
            data = source_collection.get(
                limit=limit,
                offset=offset,
                include=['embeddings', 'documents', 'metadatas']
            )

            if not data or 'ids' not in data or not data['ids']:
                print(f"[警告] 批次 {offset}-{offset+limit} 获取失败，跳过")
                continue

            # 写入目标collection
            target_collection.upsert(
                ids=data['ids'],
                embeddings=data['embeddings'],
                documents=data['documents'],
                metadatas=data['metadatas']
            )

            total_copied += len(data['ids'])
            print(f"[进度] 已复制 {total_copied}/{source_count} 条 ({total_copied*100//source_count}%)")

        # 验证复制结果
        target_count = target_collection.count()
        print(f"\n[验证] 目标collection记录数: {target_count} 条")

        if target_count >= source_count:
            print(f"[成功] 复制完成！({target_count}/{source_count})")
            return True
        else:
            print(f"[警告] 目标记录数少于源记录数 ({target_count}/{source_count})")
            return False

    except Exception as e:
        print(f"[错误] 复制失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""

    print("\n" + "="*80)
    print("从 personal_agent 复制向量数据到 message_platform")
    print("="*80)

    # 路径配置
    source_path = "d:/TechWork/personal_agent/data/chromadb"
    target_path = "./data/chromadb_mp"

    print(f"\n源路径: {source_path}")
    print(f"目标路径: {target_path}")

    # 迁移映射
    migrations = [
        ("personal_agent_tonghuashun_messages", "tonghuashun"),
        ("personal_agent_kr36", "kr36"),
        ("personal_agent_arxiv_messages", "arxiv")
    ]

    print("\n迁移计划:")
    for source, target in migrations:
        print(f"  {source} → {target}")

    # 连接ChromaDB
    try:
        print("\n[连接] 正在连接数据库...")
        source_client = chromadb.PersistentClient(path=source_path)
        target_client = chromadb.PersistentClient(path=target_path)
        print("[连接] 数据库连接成功")

    except Exception as e:
        print(f"[错误] 数据库连接失败: {e}")
        sys.exit(1)

    # 执行迁移
    success_count = 0
    total_count = len(migrations)

    for source_name, target_name in migrations:
        if copy_collection(source_client, target_client, source_name, target_name):
            success_count += 1

    # 总结
    print("\n" + "="*80)
    print("迁移完成")
    print("="*80)
    print(f"\n成功: {success_count}/{total_count} 个collection")

    if success_count == total_count:
        print("\n✓ 所有数据迁移成功！")
        return 0
    else:
        print(f"\n⚠ {total_count - success_count} 个collection迁移失败")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
