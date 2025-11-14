# -*- coding: utf-8 -*-

"""
AISI采集器测试脚本
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径到sys.path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.sources.aisi.collector import AISICollector
from backend.database.connection import create_session
from backend.database.entities import AISIMessage


async def test_collector():
    """测试AISI采集器"""

    # 从数据库读取配置
    with create_session() as db:
        from backend.database.entities import MessageSource
        source = db.query(MessageSource).filter(MessageSource.name == 'aisi').first()

        if not source:
            print("❌ 未找到AISI消息源配置")
            return

        config = {
            'id': source.id,
            'interval': 86400,
            'mysql_table': source.config.get('mysql_table'),
            'chroma_collection': source.config.get('chroma_collection'),
            'config': source.config
        }

    print(f"✓ 消息源配置加载成功")
    print(f"  - ID: {config['id']}")
    print(f"  - MySQL表: {config['mysql_table']}")
    print(f"  - ChromaDB集合: {config['chroma_collection']}")
    print()

    # 初始化采集器
    collector = AISICollector(config)

    print("正在初始化采集器...")
    if not await collector.initialize():
        print("❌ 采集器初始化失败")
        return

    print("✓ 采集器初始化成功")
    print()

    # 执行单次采集
    print("开始采集...")
    try:
        await collector._collect_once()
        print("✓ 采集完成")
    except Exception as e:
        print(f"❌ 采集失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await collector.stop()

    print()

    # 验证数据库记录
    with create_session() as db:
        count = db.query(AISIMessage).filter(
            AISIMessage.source_id == config['id']
        ).count()

        print(f"✓ 数据库中共有 {count} 条AISI消息")

        if count > 0:
            # 显示最新的3条记录
            latest_records = db.query(AISIMessage).filter(
                AISIMessage.source_id == config['id']
            ).order_by(
                AISIMessage.published_at.desc()
            ).limit(3).all()

            print()
            print("最新的3条记录：")
            for idx, record in enumerate(latest_records, 1):
                print(f"\n{idx}. {record.title}")
                print(f"   URL: {record.url}")
                print(f"   发布时间: {record.published_at}")
                print(f"   分类: {record.content_type}")
                print(f"   摘要长度: {len(record.summary) if record.summary else 0} 字符")
                if record.summary:
                    print(f"   摘要预览: {record.summary[:100]}...")


if __name__ == '__main__':
    asyncio.run(test_collector())
