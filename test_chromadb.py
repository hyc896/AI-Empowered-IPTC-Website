#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试ChromaDB初始化
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_chromadb_init():
    """测试ChromaDB初始化"""
    try:
        print("=== 测试ChromaDB初始化 ===")

        # 1. 加载配置
        print("1. 加载配置...")
        from backend.config.config_manager import ConfigManager
        config_manager = ConfigManager()
        success = config_manager.load_config("config.yaml")

        if not success:
            print("❌ 配置加载失败")
            return False

        config = config_manager.get_config()
        print("配置加载成功")

        # 2. 获取ChromaDB配置
        print("2. 获取ChromaDB配置...")
        chromadb_config = config.get("database", {}).get("chromadb", {})
        if not chromadb_config:
            print("❌ 未找到ChromaDB配置")
            return False

        print(f"✅ ChromaDB配置: {chromadb_config}")

        # 3. 初始化ChromaDB
        print("3. 初始化ChromaDB...")
        from backend.storage import initialize_chromadb, get_chromadb_storage

        result = initialize_chromadb(chromadb_config)
        if not result:
            print("❌ ChromaDB初始化失败")
            return False

        print("✅ ChromaDB初始化成功")

        # 4. 验证初始化状态
        print("4. 验证初始化状态...")
        storage = get_chromadb_storage()
        if not storage.is_initialized():
            print("❌ ChromaDB状态检查失败")
            return False

        print("✅ ChromaDB状态正常")

        # 5. 测试基本操作
        print("5. 测试基本操作...")
        test_collection = storage._collections.get("news")
        if not test_collection:
            print("❌ 未找到news collection")
            return False

        print("✅ Collection可用")

        # 6. 检查数据目录
        print("6. 检查数据目录...")
        chromadb_path = chromadb_config.get("path", "./data/chromadb")
        if os.path.exists(chromadb_path):
            print(f"✅ ChromaDB数据目录存在: {chromadb_path}")
        else:
            print(f"⚠️ ChromaDB数据目录不存在，将在首次使用时创建: {chromadb_path}")

        print("\n=== 🎉 ChromaDB测试全部通过！ ===")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_chromadb_init()
    sys.exit(0 if success else 1)