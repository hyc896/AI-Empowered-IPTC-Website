# -*- coding: utf-8 -*-

"""
IEAI采集器测试脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.sources.ieai.collector import IEAICollector
from backend.database.connection import create_session
from backend.database.entities import MessageSource


async def test_ieai_collector():
    """测试IEAI采集器"""
    print("=" * 60)
    print("IEAI采集器测试")
    print("=" * 60)

    # 从数据库获取IEAI消息源配置
    with create_session() as db:
        source = db.query(MessageSource).filter(
            MessageSource.name == 'ieai'
        ).first()

        if not source:
            print("[ERROR] 错误：未找到IEAI消息源配置")
            return

        config = {
            "id": source.id,
            "name": source.name,
            "adapter_name": source.adapter_name,
            "category": source.category,
            "display_name": source.display_name,
            "mysql_table": source.config.get("mysql_table", "mp_ieai_messages"),
            "chroma_collection": source.config.get("chroma_collection", "ieai"),
            "config": source.config,
            "interval": source.config.get("interval", 86400)
        }

    print(f"[OK] 加载消息源配置:")
    print(f"  - ID: {config['id']}")
    print(f"  - 名称: {config['display_name']}")
    print(f"  - URL: {config['config'].get('url')}")
    print(f"  - 采集间隔: {config['interval']}秒")
    print()

    # 创建采集器实例
    collector = IEAICollector(config)

    # 初始化采集器
    print("正在初始化采集器...")
    if not await collector.initialize():
        print("[ERROR] 采集器初始化失败")
        return

    print("[OK] 采集器初始化成功")
    print()

    # 执行一次采集
    print("开始执行采集...")
    print("-" * 60)
    try:
        await collector._collect_once()
        print("-" * 60)
        print("[OK] 采集完成")
    except Exception as e:
        print(f"[ERROR] 采集失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await collector.stop()

    # 检查数据库结果
    print()
    print("检查数据库结果:")
    with create_session() as db:
        from backend.database.entities import IEAIMessage
        count = db.query(IEAIMessage).filter(
            IEAIMessage.source_id == config['id']
        ).count()
        print(f"  - 数据库记录总数: {count}")

        if count > 0:
            latest = db.query(IEAIMessage).filter(
                IEAIMessage.source_id == config['id']
            ).order_by(IEAIMessage.crawled_at.desc()).first()

            print(f"  - 最新记录:")
            print(f"    标题: {latest.title}")
            print(f"    URL: {latest.url}")
            print(f"    作者: {latest.provider}")
            print(f"    发布时间: {latest.published_at}")
            print(f"    摘要长度: {len(latest.summary) if latest.summary else 0}字")
            print(f"    内容长度: {len(latest.content)}字")

    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    # Windows环境需要设置事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(test_ieai_collector())
