#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
诊断ChromaDB数据库问题
"""

import os
import sys
import sqlite3

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def diagnose_chromadb():
    """诊断ChromaDB问题"""
    print("=== ChromaDB诊断开始 ===")

    # 1. 检查文件系统
    print("\n1. 文件系统检查:")
    db_path = "./data/chromadb/chroma.sqlite3"

    if os.path.exists(db_path):
        size_mb = os.path.getsize(db_path) / (1024 * 1024)
        print(f"  ✅ 数据库文件存在: {db_path}")
        print(f"  ✅ 文件大小: {size_mb:.2f} MB")

        # 检查SQLite内容
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print(f"  ✅ SQLite表数量: {len(tables)}")

            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"    - {table_name}: {count}条记录")

            conn.close()

        except Exception as e:
            print(f"  ❌ SQLite访问失败: {e}")
    else:
        print(f"  ❌ 数据库文件不存在: {db_path}")
        return

    # 2. 检查ChromaDB连接
    print("\n2. ChromaDB连接检查:")
    try:
        import chromadb

        # 尝试不同的路径
        paths_to_try = [
            "./data/chromadb",
            os.path.abspath("./data/chromadb"),
            "data/chromadb",
            "../data/chromadb"
        ]

        for path in paths_to_try:
            print(f"  尝试路径: {path}")
            try:
                client = chromadb.PersistentClient(path=path)
                collections = client.list_collections()
                print(f"    ✅ 连接成功，找到 {len(collections)} 个collections")

                total_data = 0
                for collection in collections:
                    count = collection.count()
                    total_data += count
                    print(f"      - {collection.name}: {count}条")

                print(f"    总数据量: {total_data}条")

                if total_data > 0:
                    print(f"  ✅ 找到有效数据，使用路径: {path}")
                    break
                else:
                    print(f"  ⚠️ 路径 {path} 连接成功但无数据")

            except Exception as e:
                print(f"    ❌ 连接失败: {e}")

    except Exception as e:
        print(f"  ❌ ChromaDB导入失败: {e}")

    # 3. 检查工作目录
    print("\n3. 工作目录检查:")
    current_dir = os.getcwd()
    print(f"  当前工作目录: {current_dir}")
    print(f"  相对路径解析: {os.path.abspath('./data/chromadb')}")

    print("\n=== 诊断完成 ===")

if __name__ == "__main__":
    diagnose_chromadb()