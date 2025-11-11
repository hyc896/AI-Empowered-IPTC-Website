# -*- coding: utf-8 -*-

"""
清空Partnership AI数据（MySQL + ChromaDB）
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.storage import initialize_chromadb, get_chromadb_storage
from backend.config.config_manager import ConfigManager
from backend.database.connection import create_session
from backend.database.entities import PartnershipAIMessage

print("=== 清空Partnership AI数据 ===\n")

# 1. 清空MySQL
print("【1/2】清空MySQL数据...")
try:
    with create_session() as db:
        count = db.query(PartnershipAIMessage).count()
        db.query(PartnershipAIMessage).delete()
        db.commit()
        print(f"✓ MySQL清空成功，删除了 {count} 条记录")
except Exception as e:
    print(f"✗ MySQL清空失败: {e}")

# 2. 清空ChromaDB
print("\n【2/2】清空ChromaDB数据...")
try:
    config_path = project_root / 'config.yaml'
    config_manager = ConfigManager()
    config_manager.load_config(str(config_path))
    config_data = config_manager.get_config()

    chromadb_config = config_data.get("database", {}).get("chromadb", {})
    initialize_chromadb(chromadb_config)

    storage = get_chromadb_storage()

    # 删除并重建集合
    collection_name = "partnership_ai_blog"
    try:
        storage.delete_collection(collection_name)
        print(f"✓ 删除旧集合: {collection_name}")
    except Exception:
        print(f"  (集合不存在，跳过删除)")

    storage.create_collection(collection_name)
    print(f"✓ 创建新集合: {collection_name}")

    print(f"✓ ChromaDB清空成功")
except Exception as e:
    print(f"✗ ChromaDB清空失败: {e}")

print("\n=== 清空完成 ===")
