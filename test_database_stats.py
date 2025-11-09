#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试数据库统计功能
"""

import asyncio
import sys
import os

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

async def test_database_stats():
    """测试数据库统计功能"""
    try:
        # 初始化配置
        from backend.config.config_manager import ConfigManager
        config_manager = ConfigManager()
        config_manager.load_config("config.yaml")

        # 模拟app_state
        app_state = {}

        # 初始化数据库
        from backend.database.connection import init_database
        init_database()
        app_state["db_config"] = {"database": "message_platform"}

        # 初始化存储
        from backend.storage import initialize_chromadb, get_chromadb_storage
        chromadb_config = {
            'mode': 'local',
            'path': './data/chromadb'
        }
        result = initialize_chromadb(chromadb_config)
        if result:
            app_state["storage"] = get_chromadb_storage()

        # 导入统计函数
        from backend.main import display_database_stats

        # 修改函数中的app_state引用
        import backend.main
        original_app_state = getattr(backend.main, 'app_state', {})
        backend.main.app_state = app_state

        # 执行统计
        await display_database_stats()

        print("Database stats test completed successfully!")

    except Exception as e:
        print(f"Database stats test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_database_stats())