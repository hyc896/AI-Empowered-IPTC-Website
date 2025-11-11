# -*- coding: utf-8 -*-

"""
测试RAND Collector采集功能
"""

import asyncio
import sys
import os

# Windows控制台UTF-8编码
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加项目根目录到Python路径
sys.path.insert(0, 'D:/TechWork/message_platform')

from backend.database.entities import MessageSource, RANDMessage
from backend.database.connection import create_session
from backend.sources.rand.collector import RANDCollector

async def test_rand_collector():
    """测试RAND采集器"""

    # 1. 连接数据库，获取消息源配置
    with create_session() as session:
        # 查询RAND消息源
        source = session.query(MessageSource).filter(
            MessageSource.name == 'rand_ai'
        ).first()

        if not source:
            print("❌ 错误：未找到 rand_ai 消息源，请先执行 register.sql")
            return

        print(f"✓ 找到消息源：{source.display_name}")
        print(f"  ID: {source.id}")
        print(f"  URL: {source.config.get('url')}")
        print(f"  is_active: {source.is_active}")

        # 2. 创建采集器配置
        collector_config = {
            'id': source.id,
            'interval': source.config.get('interval', 86400),
            'mysql_table': source.config.get('mysql_table'),
            'chroma_collection': source.config.get('chroma_collection'),
            'config': source.config
        }

    # 3. 初始化采集器
    collector = RANDCollector(collector_config)

    print("\n正在初始化采集器...")
    success = await collector.initialize()

    if not success:
        print("❌ 采集器初始化失败")
        return

    print("✓ 采集器初始化成功")

    # 4. 执行采集
    print("\n开始采集RAND文章...")
    await collector._collect_once()

    # 5. 查询数据库验证结果
    print("\n查询数据库验证采集结果...")
    with create_session() as session:
        messages = session.query(RANDMessage).filter(
            RANDMessage.source_id == collector.source_id
        ).order_by(
            RANDMessage.published_at.desc()
        ).limit(5).all()

        print(f"\n✓ 数据库中共有 {session.query(RANDMessage).count()} 条RAND消息")

        if messages:
            print("\n最新5条消息：")
            for idx, msg in enumerate(messages, 1):
                print(f"\n[{idx}] {msg.title}")
                print(f"    ID: {msg.id}")
                print(f"    External ID: {msg.external_id}")
                print(f"    URL: {msg.url}")
                print(f"    Category: {msg.category}")
                print(f"    Published: {msg.published_at}")
                print(f"    Provider: {msg.provider[:100] if msg.provider else 'N/A'}")
                print(f"    Summary (前100字): {msg.summary[:100] if msg.summary else 'N/A'}...")
                print(f"    Content length: {len(msg.content)} chars")
        else:
            print("⚠ 数据库中没有数据，可能采集失败或所有文章已存在")

    # 6. 关闭采集器
    await collector.stop()
    print("\n✓ 采集器已关闭")

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(test_rand_collector())
