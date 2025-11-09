#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试ChromaDB历史数据访问
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_chromadb_data():
    """测试ChromaDB历史数据访问"""
    try:
        print("=== 测试ChromaDB历史数据访问 ===")

        # 1. 初始化ChromaDB
        print("1. 初始化ChromaDB...")
        from backend.config.config_manager import ConfigManager
        config_manager = ConfigManager()
        config_manager.load_config("config.yaml")

        config = config_manager.get_config()
        chromadb_config = config.get("database", {}).get("chromadb", {})

        from backend.storage import initialize_chromadb, get_chromadb_storage
        result = initialize_chromadb(chromadb_config)

        if not result:
            print("ChromaDB初始化失败")
            return False

        storage = get_chromadb_storage()
        print("ChromaDB初始化成功")

        # 2. 检查现有数据
        print("2. 检查现有collections...")
        client = storage._client

        # 获取所有collections
        collections = client.list_collections()
        print(f"找到 {len(collections)} 个collections:")

        for collection in collections:
            print(f"  - Collection: {collection.name}")
            try:
                count = collection.count()
                print(f"    数据量: {count} 条")

                if count > 0:
                    # 获取一些样本数据
                    result = collection.get(limit=2)
                    if result and result['documents']:
                        print(f"    样本数据: {result['documents'][0][:100]}...")

            except Exception as e:
                print(f"    访问collection失败: {e}")

        # 3. 测试新的消息平台collection
        print("3. 测试消息平台专用collections...")
        news_collection = storage._collections.get("news")
        if news_collection:
            news_count = news_collection.count()
            print(f"News collection数据量: {news_count}")
        else:
            print("News collection未创建")

        chat_collection = storage._collections.get("chat_history")
        if chat_collection:
            chat_count = chat_collection.count()
            print(f"Chat history collection数据量: {chat_count}")
        else:
            print("Chat history collection未创建")

        memory_collection = storage._collections.get("memory")
        if memory_collection:
            memory_count = memory_collection.count()
            print(f"Memory collection数据量: {memory_count}")
        else:
            print("Memory collection未创建")

        print("\n=== ChromaDB数据访问测试完成！ ===")
        return True

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_chromadb_data()
    sys.exit(0 if success else 1)