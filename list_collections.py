#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查看ChromaDB中的所有集合"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.storage.chromadb_storage import ChromaDBStorage
from backend.config.config_manager import ConfigManager

def main():
    config_manager = ConfigManager()
    config_manager.load_config('config.yaml')
    config = config_manager.get_config()
    chroma_config = config.get('database', {}).get('chromadb', {})

    storage = ChromaDBStorage()
    storage.initialize(chroma_config)

    # 获取所有集合
    collections = storage._client.list_collections()

    print("=" * 60)
    print(f"ChromaDB中的集合（共 {len(collections)} 个）：")
    print("=" * 60)

    for collection in collections:
        count = collection.count()
        print(f"\n集合名称: {collection.name}")
        print(f"文档数量: {count}")

if __name__ == "__main__":
    main()
