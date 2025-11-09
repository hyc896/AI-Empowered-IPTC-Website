#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试数据库表创建脚本
用于验证数据库连接和表结构是否正确
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database.connection import init_database, get_database_info
from backend.database.entities import Base

def test_database_creation():
    """测试数据库表创建"""
    print("=== Test Database Table Creation ===")

    try:
        # 初始化数据库连接和创建表
        print("Initializing database connection...")
        success = init_database()

        if not success:
            print("FAIL: Database initialization failed")
            return False

        print("OK: Database initialized successfully")

        # 获取数据库信息
        print("Getting database information...")
        info = get_database_info()

        print(f"Database: {info.get('database')}")
        print(f"Host: {info.get('host')}:{info.get('port')}")
        print(f"Version: {info.get('version')}")
        print(f"Total tables: {info.get('total_tables', 0)}")
        print(f"Total rows: {info.get('total_rows', 0)}")

        # 显示表详情
        tables = info.get('tables', [])
        if tables:
            print("\nTable details:")
            for table in tables:
                print(f"  {table['name']}: {table['rows']} rows "
                      f"({table['total_size']} bytes)")
        else:
            print("\nWARNING: No tables found, tables may not be created yet")

        print("OK: Database test completed")
        return True

    except Exception as e:
        print(f"FAIL: Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_database_creation()