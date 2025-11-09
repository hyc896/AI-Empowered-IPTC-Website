#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_real_collections():
    try:
        import chromadb

        # 强制重新连接
        client = chromadb.PersistentClient(path="./data/chromadb")

        print("ChromaDB连接成功")

        collections = client.list_collections()
        print(f"找到 {len(collections)} 个collections:")

        for collection in collections:
            try:
                count = collection.count()
                print(f"  {collection.name}: {count}条数据")

                if count > 0:
                    # 获取前2条数据的元数据
                    result = collection.get(limit=2)
                    if result and result['metadatas']:
                        print(f"    样本1: {result['metadatas'][0].get('source', 'unknown')}")

            except Exception as e:
                print(f"  {collection.name}: 访问失败 - {e}")

    except Exception as e:
        print(f"检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_real_collections()