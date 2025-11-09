#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查ChromaDB中实际的collections
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_collections():
    """检查所有collections"""
    try:
        import chromadb

        # 连接到ChromaDB
        client = chromadb.PersistentClient(path="./data/chromadb")
        print("ChromaDB连接成功")

        # 获取所有collections
        collections = client.list_collections()
        print(f"\n找到 {len(collections)} 个collections:")

        for collection in collections:
            try:
                count = collection.count()
                print(f"  {collection.name}: {count}条数据")

                # 如果有数据，获取一些样本
                if count > 0:
                    sample = collection.get(limit=1)
                    if sample and sample['metadatas']:
                        print(f"    样本元数据: {sample['metadatas'][0]}")
            except Exception as e:
                print(f"  {collection.name}: 访问失败 - {e}")

        # 检查数据库文件
        db_path = "./data/chromadb/chroma.sqlite3"
        if os.path.exists(db_path):
            size_mb = os.path.getsize(db_path) / (1024 * 1024)
            print(f"\n数据库文件大小: {size_mb:.2f} MB")
        else:
            print("\n数据库文件不存在")

    except Exception as e:
        print(f"检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_collections()