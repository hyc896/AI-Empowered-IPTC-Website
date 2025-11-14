# -*- coding: utf-8 -*-

"""
清理VentureBeat数据脚本

删除：
1. ChromaDB的venturebeat collection
2. MySQL的mp_venturebeat_messages表数据
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.storage import get_chromadb_storage
from backend.database.connection import create_session
from backend.database.entities import VentureBeatMessage
from backend.config import ConfigManager


def main():
    print("=" * 60)
    print("清理VentureBeat数据")
    print("=" * 60)

    # 1. 删除ChromaDB collection
    try:
        # 显式初始化ChromaDB（遵循铁律3）
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        config_path = os.path.join(project_root, 'config.yaml')

        config_manager = ConfigManager()
        config_manager.load_config(config_path)
        chroma_config = config_manager.get_config('database.chromadb') or {}

        chroma_storage = get_chromadb_storage()

        # 如果未初始化，先初始化
        if not chroma_storage.is_initialized():
            print("\n【初始化】ChromaDB未初始化，正在初始化...")
            chroma_storage.initialize(chroma_config)
            print("  [OK] ChromaDB初始化成功")

        print("\n【步骤1】删除ChromaDB的venturebeat collection...")

        # 检查collection是否存在
        try:
            collection = chroma_storage._client.get_collection(name="venturebeat")
            count = collection.count()
            print(f"  - 找到venturebeat collection，包含 {count} 条向量")

            # 删除collection
            chroma_storage._client.delete_collection(name="venturebeat")
            print("  [OK] ChromaDB collection已删除")
        except Exception as e:
            if "does not exist" in str(e).lower():
                print("  - venturebeat collection不存在，跳过")
            else:
                raise
    except Exception as e:
        print(f"  [ERROR] ChromaDB清理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 2. 清空MySQL表
    try:
        print("\n【步骤2】清空MySQL的mp_venturebeat_messages表...")
        with create_session() as db:
            count = db.query(VentureBeatMessage).count()
            print(f"  - 找到 {count} 条记录")

            if count > 0:
                db.query(VentureBeatMessage).delete()
                db.commit()
                print(f"  [OK] 已删除 {count} 条记录")
            else:
                print("  - 表为空，无需清理")
    except Exception as e:
        print(f"  [ERROR] MySQL清理失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("清理完成！")
    print("=" * 60)
    print("\n提示：重启message_platform服务后，VentureBeat采集器将重新采集数据")
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
