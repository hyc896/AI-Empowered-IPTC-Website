#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import os

def check_sqlite_collections():
    db_path = "./data/chromadb/chroma.sqlite3"

    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return

    print(f"数据库文件: {db_path}")
    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    print(f"文件大小: {size_mb:.2f} MB")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 查看collections表
        print("\n=== Collections表 ===")
        cursor.execute("SELECT * FROM collections")
        collections = cursor.fetchall()
        for collection in collections:
            print(f"Collection: {collection}")

        # 查看collection_metadata表
        print("\n=== Collection Metadata ===")
        cursor.execute("SELECT * FROM collection_metadata")
        metadata = cursor.fetchall()
        for meta in metadata:
            print(f"Metadata: {meta}")

        # 查看embeddings表
        print("\n=== Embeddings数据 ===")
        cursor.execute("SELECT COUNT(*) FROM embeddings")
        embedding_count = cursor.fetchone()[0]
        print(f"Embeddings总数: {embedding_count}")

        if embedding_count > 0:
            cursor.execute("SELECT * FROM embeddings LIMIT 3")
            embeddings = cursor.fetchall()
            for emb in embeddings:
                print(f"Embedding样本: {emb}")

        conn.close()

    except Exception as e:
        print(f"SQLite查询失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_sqlite_collections()