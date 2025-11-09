#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sqlite3

def diagnose():
    print("=== ChromaDB诊断 ===")

    db_path = "./data/chromadb/chroma.sqlite3"

    if os.path.exists(db_path):
        size_mb = os.path.getsize(db_path) / (1024 * 1024)
        print(f"数据库文件: {db_path}")
        print(f"文件大小: {size_mb:.2f} MB")

        # 检查SQLite内容
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print(f"SQLite表数量: {len(tables)}")

            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  {table_name}: {count}条记录")

            conn.close()

        except Exception as e:
            print(f"SQLite访问失败: {e}")
    else:
        print(f"数据库文件不存在: {db_path}")

    # 检查ChromaDB连接
    try:
        import chromadb

        client = chromadb.PersistentClient(path="./data/chromadb")
        collections = client.list_collections()
        print(f"ChromaDB collections数量: {len(collections)}")

        for collection in collections:
            count = collection.count()
            print(f"  {collection.name}: {count}条数据")

    except Exception as e:
        print(f"ChromaDB连接失败: {e}")

if __name__ == "__main__":
    diagnose()