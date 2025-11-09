# -*- coding: utf-8 -*-

"""
列出ChromaDB中的所有collection及其记录数
用于验证向量数据状态
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.config.config_manager import ConfigManager
import chromadb

def list_chromadb_collections():
    """列出所有ChromaDB collection"""

    print("\n" + "=" * 80)
    print("CHROMADB - Collection列表")
    print("=" * 80)

    # 读取配置
    try:
        config_manager = ConfigManager()
        config_manager.load_config("config.yaml")
        config = config_manager.get_config()

        chromadb_config = config.get("database", {}).get("chromadb", {})
        chromadb_path = chromadb_config.get("path", "./data/chromadb_mp")

        print(f"\nChromaDB路径: {chromadb_path}")

    except Exception as e:
        print(f"配置加载失败: {e}")
        chromadb_path = "./data/chromadb_mp"
        print(f"使用默认路径: {chromadb_path}")

    # 连接ChromaDB
    try:
        client = chromadb.PersistentClient(path=chromadb_path)
        collections = client.list_collections()

        print(f"\n找到 {len(collections)} 个collection:")
        print("-" * 80)

        if not collections:
            print("\n[提示] 未找到任何collection，ChromaDB为空")
        else:
            total_records = 0
            for collection in collections:
                try:
                    count = collection.count()
                    total_records += count
                    print(f"\nCollection: {collection.name}")
                    print(f"  记录数: {count} 条")
                    print(f"  Metadata: {collection.metadata}")
                except Exception as e:
                    print(f"\nCollection: {collection.name}")
                    print(f"  记录数: [查询失败] - {e}")

            print("\n" + "-" * 80)
            print(f"\n总计: {total_records} 条向量记录")

    except Exception as e:
        print(f"\n[错误] ChromaDB连接失败: {e}")
        print(f"请确认路径是否正确: {chromadb_path}")

    print("\n" + "=" * 80)
    print("检查完成")
    print("=" * 80 + "\n")

if __name__ == '__main__':
    list_chromadb_collections()
