# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.storage import get_chromadb_storage
from backend.config import ConfigManager

def main():
    cm = ConfigManager()
    cm.load_config('config.yaml')

    chroma_storage = get_chromadb_storage()
    chroma_storage.initialize(cm.get_config('database.chromadb'))

    collections = chroma_storage._client.list_collections()

    venturebeat_found = False
    for c in collections:
        if 'venturebeat' in c.name.lower():
            print(f"找到: {c.name}, 向量数量: {c.count()}")
            venturebeat_found = True

    if not venturebeat_found:
        print("✓ venturebeat collection已完全清除")
    else:
        print("✗ venturebeat collection仍然存在")

if __name__ == '__main__':
    main()
