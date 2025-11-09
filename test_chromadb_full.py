#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
全面检查ChromaDB数据
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_full_chromadb():
    """全面检查ChromaDB数据"""
    try:
        print("=== 全面检查ChromaDB数据 ===")

        # 1. 初始化ChromaDB
        from backend.config.config_manager import ConfigManager
        config_manager = ConfigManager()
        config_manager.load_config("config.yaml")

        config = config_manager.get_config()
        chromadb_config = config.get("database", {}).get("chromadb", {})

        from backend.storage import initialize_chromadb, get_chromadb_storage
        result = initialize_chromadb(chromadb_config)

        storage = get_chromadb_storage()
        client = storage._client

        # 2. 获取所有collections（包括可能的历史数据）
        print("2. 检查所有collections...")
        all_collections = client.list_collections()

        total_data = 0
        for collection in all_collections:
            try:
                count = collection.count()
                total_data += count
                print(f"  Collection: {collection.name}")
                print(f"    数据量: {count} 条")

                if count > 0:
                    # 获取元数据样本
                    sample = collection.get(limit=1)
                    if sample and sample['metadatas']:
                        print(f"    元数据样本: {sample['metadatas'][0]}")

            except Exception as e:
                print(f"    访问失败: {e}")

        print(f"\n总数据量: {total_data} 条")

        # 3. 尝试找到可能的历史数据collection
        print("\n3. 查找可能的历史数据...")
        historical_collections = []
        for collection in all_collections:
            if 'chat' in collection.name.lower() or 'news' in collection.name.lower() or 'memory' in collection.name.lower():
                if collection.count() > 0:
                    historical_collections.append(collection.name)

        if historical_collections:
            print(f"找到包含数据的collections: {historical_collections}")
        else:
            print("未找到包含历史数据的collections")

        # 4. 检查数据库文件大小
        print("\n4. 检查数据库文件...")
        db_path = "./data/chromadb/chroma.sqlite3"
        if os.path.exists(db_path):
            size_mb = os.path.getsize(db_path) / (1024 * 1024)
            print(f"数据库文件大小: {size_mb:.2f} MB")

            if size_mb > 50:  # 如果文件大于50MB，应该有数据
                print("数据库文件较大，应该包含历史数据")
            else:
                print("数据库文件较小，可能是新创建的")
        else:
            print("数据库文件不存在")

        return True

    except Exception as e:
        print(f"检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_full_chromadb()