# -*- coding: utf-8 -*-

"""
Axios采集器测试脚本
"""

import asyncio
import logging
from backend.sources.axios.collector import AxiosCollector
from backend.database.connection import create_session
from backend.database.entities import AxiosMessage

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_axios_collector():
    """测试Axios采集器"""

    # 从数据库获取配置
    with create_session() as db:
        from backend.database.entities import MessageSource
        source = db.query(MessageSource).filter(MessageSource.name == 'axios').first()

        if not source:
            print("错误: 未找到axios消息源配置")
            return

        config = {
            'id': source.id,
            'interval': source.config.get('interval', 3600) if source.config else 3600,
            'config': source.config
        }

    print(f"消息源ID: {config['id']}")
    print(f"配置: {config['config']}")

    # 创建采集器
    collector = AxiosCollector(config)

    # 初始化
    if not await collector.initialize():
        print("采集器初始化失败")
        return

    print("\n开始测试采集...")

    # 执行一次采集
    await collector._collect_once()

    # 检查数据库
    with create_session() as db:
        count = db.query(AxiosMessage).filter(
            AxiosMessage.source_id == config['id']
        ).count()

        print(f"\n采集完成！数据库中共有 {count} 条Axios消息")

        # 显示最新的5条
        latest = db.query(AxiosMessage).filter(
            AxiosMessage.source_id == config['id']
        ).order_by(
            AxiosMessage.published_at.desc()
        ).limit(5).all()

        print("\n最新的5条消息:")
        for i, msg in enumerate(latest, 1):
            print(f"\n{i}. {msg.title}")
            print(f"   URL: {msg.url}")
            print(f"   发布时间: {msg.published_at}")
            print(f"   地区: {msg.region}")
            print(f"   行业标签: {msg.industry_tags}")
            print(f"   AI标签: {msg.ai_tag}")
            print(f"   内容预览: {msg.content[:200] if msg.content else 'N/A'}...")

if __name__ == "__main__":
    asyncio.run(test_axios_collector())
