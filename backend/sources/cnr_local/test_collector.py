# -*- coding: utf-8 -*-

"""
中央广播电视总台地方新闻采集器测试脚本
"""

import asyncio
import logging
from backend.sources.cnr_local.collector import CNRLocalCollector
from backend.database.connection import create_session
from backend.database.entities import CNRLocalMessage

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_cnr_local_collector():
    """测试CNR地方新闻采集器"""

    # 从数据库获取配置
    with create_session() as db:
        from backend.database.entities import MessageSource
        source = db.query(MessageSource).filter(MessageSource.name == 'cnr_local').first()

        if not source:
            print("错误: 未找到cnr_local消息源配置")
            return

        config = {
            'id': source.id,
            'mysql_table': source.config.get('mysql_table', 'mp_cnr_local_messages'),
            'chroma_collection': source.config.get('chroma_collection', 'cnr_local'),
            'interval': source.config.get('interval', 3600) if source.config else 3600,
            'config': source.config
        }

    print(f"消息源ID: {config['id']}")
    print(f"MySQL表名: {config['mysql_table']}")
    print(f"ChromaDB集合: {config['chroma_collection']}")
    print(f"配置: {config['config']}")

    # 创建采集器
    collector = CNRLocalCollector(config)

    # 初始化
    if not await collector.initialize():
        print("采集器初始化失败")
        return

    print("\n开始测试采集...")

    # 执行一次采集
    await collector._collect_once()

    # 检查数据库
    with create_session() as db:
        count = db.query(CNRLocalMessage).filter(
            CNRLocalMessage.source_id == config['id']
        ).count()

        print(f"\n采集完成！数据库中共有 {count} 条CNR地方新闻消息")

        # 显示最新的5条
        latest = db.query(CNRLocalMessage).filter(
            CNRLocalMessage.source_id == config['id']
        ).order_by(
            CNRLocalMessage.crawled_at.desc()
        ).limit(5).all()

        print("\n最新的5条消息:")
        for i, msg in enumerate(latest, 1):
            print(f"\n{i}. {msg.title}")
            print(f"   URL: {msg.url}")
            print(f"   发布时间: {msg.published_at}")
            print(f"   地区: {msg.region}")
            print(f"   提供方: {msg.provider}")
            print(f"   内容预览: {msg.content[:100] if msg.content else 'N/A'}...")

if __name__ == "__main__":
    asyncio.run(test_cnr_local_collector())
