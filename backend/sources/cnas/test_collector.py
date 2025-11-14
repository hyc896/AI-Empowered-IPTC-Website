# -*- coding: utf-8 -*-

"""
CNAS采集器测试脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

from backend.sources.cnas.collector import CNASCollector
from backend.database.connection import create_session
from backend.database.entities import CNASMessage


async def test_collector():
    """测试CNAS采集器"""

    # 配置
    config = {
        'id': '400118e4-bef4-11f0-8cb6-00ff40160484',  # 从数据库获取的source_id
        'interval': 86400,
        'mysql_table': 'mp_cnas_messages',
        'chroma_collection': 'cnas_reports',
        'config': {
            'url': 'https://www.cnas.org/reports',
            'region': 'US',
            'timezone': 'America/New_York',
            'language': 'en'
        }
    }

    print("=== CNAS采集器测试 ===\n")

    # 创建采集器实例
    collector = CNASCollector(config)

    # 初始化
    print("1. 初始化采集器...")
    if not await collector.initialize():
        print("❌ 初始化失败")
        return
    print("✓ 初始化成功\n")

    # 执行一次采集
    print("2. 执行采集...")
    try:
        await collector._collect_once()
        print("✓ 采集完成\n")
    except Exception as e:
        print(f"❌ 采集失败: {e}\n")

    # 查询数据库验证
    print("3. 验证数据库记录...")
    with create_session() as db:
        count = db.query(CNASMessage).filter(
            CNASMessage.source_id == config['id']
        ).count()

        if count > 0:
            print(f"✓ 数据库中有 {count} 条记录")

            # 显示最新的3条记录
            latest = db.query(CNASMessage).filter(
                CNASMessage.source_id == config['id']
            ).order_by(
                CNASMessage.crawled_at.desc()
            ).limit(3).all()

            print("\n最新记录：")
            for idx, record in enumerate(latest, 1):
                print(f"\n[{idx}] {record.title}")
                print(f"    作者: {record.provider}")
                print(f"    日期: {record.published_at}")
                print(f"    分类: {record.category}")
                print(f"    URL: {record.url}")
                print(f"    摘要长度: {len(record.summary or '')} 字符")
                print(f"    内容长度: {len(record.content or '')} 字符")
        else:
            print("⚠ 数据库中没有记录")

    # 测试去重功能
    print("\n4. 测试去重功能（再次采集）...")
    try:
        await collector._collect_once()
        print("✓ 去重测试完成")

        with create_session() as db:
            new_count = db.query(CNASMessage).filter(
                CNASMessage.source_id == config['id']
            ).count()

            if new_count == count:
                print(f"✓ 去重成功：记录数量未变化 ({new_count}条)")
            else:
                print(f"⚠ 可能有新数据：{count} → {new_count} 条")
    except Exception as e:
        print(f"❌ 去重测试失败: {e}")

    # 清理
    print("\n5. 清理资源...")
    await collector.stop()
    print("✓ 清理完成")

    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    # Windows环境需要设置事件循环策略
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(test_collector())
