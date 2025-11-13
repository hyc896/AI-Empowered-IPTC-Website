# -*- coding: utf-8 -*-

"""
HSE AI Centre采集器测试脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from backend.sources.hse_ai.collector import HSEAICollector
from backend.database.connection import create_session
from backend.database.entities import HSEAIMessage


async def test_collector():
    """测试采集器"""

    # 从数据库获取消息源配置
    with create_session() as db:
        from backend.database.entities import MessageSource
        source = db.query(MessageSource).filter(MessageSource.name == 'hse_ai').first()

        if not source:
            print("错误：未找到hse_ai消息源配置")
            return

        print(f"消息源ID: {source.id}")
        print(f"消息源名称: {source.display_name}")
        print(f"配置: {source.config}")

        # 构建采集器配置
        config = {
            'id': source.id,
            'interval': 86400,
            'mysql_table': source.config.get('mysql_table'),
            'chroma_collection': source.config.get('chroma_collection'),
            'config': source.config
        }

    # 创建采集器实例
    collector = HSEAICollector(config)

    # 初始化
    print("\n初始化采集器...")
    if not await collector.initialize():
        print("初始化失败")
        return

    print("初始化成功")

    # 执行单次采集
    print("\n开始采集...")
    await collector._collect_once()

    # 查询数据库验证
    print("\n验证数据库...")
    with create_session() as db:
        count = db.query(HSEAIMessage).filter(
            HSEAIMessage.source_id == source.id
        ).count()
        print(f"数据库中共有 {count} 条HSE AI消息")

        # 显示最新的3条
        latest = db.query(HSEAIMessage).filter(
            HSEAIMessage.source_id == source.id
        ).order_by(
            HSEAIMessage.published_at.desc()
        ).limit(3).all()

        print("\n最新3条消息：")
        for idx, msg in enumerate(latest, 1):
            print(f"\n{idx}. {msg.title}")
            print(f"   URL: {msg.url}")
            print(f"   发布时间: {msg.published_at}")
            print(f"   外部ID: {msg.external_id}")
            print(f"   内容长度: {len(msg.content)} 字符")
            print(f"   摘要长度: {len(msg.summary) if msg.summary else 0} 字符")
            if msg.summary:
                print(f"   摘要预览: {msg.summary[:100]}...")

    # 关闭采集器
    await collector.stop()
    print("\n测试完成")


if __name__ == "__main__":
    asyncio.run(test_collector())
