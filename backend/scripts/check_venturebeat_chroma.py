# -*- coding: utf-8 -*-

"""
检查VentureBeat在ChromaDB中的状态
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.storage import get_chromadb_storage


def main():
    chroma_storage = get_chromadb_storage()

    if not chroma_storage or not chroma_storage.is_initialized():
        print("ChromaDB未初始化")
        return

    try:
        collection = chroma_storage._client.get_collection(name="venturebeat")
        count = collection.count()
        print(f"venturebeat collection: {count} 条向量")
    except Exception as e:
        if "does not exist" in str(e).lower():
            print("venturebeat collection不存在")
        else:
            print(f"错误: {e}")


if __name__ == '__main__':
    main()
