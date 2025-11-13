# -*- coding: utf-8 -*-

"""
Stellenbosch Collector测试脚本
用于验证采集器功能
"""

import asyncio
import sys
import os
import logging

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from backend.sources.stellenbosch.collector import StellenboschCollector
from backend.database.connection import create_session
from backend.database.entities import StellenboschMessage

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_collector():
    """测试采集器"""
    # 查询消息源配置
    with create_session() as db:
        from backend.database.entities import MessageSource
        source = db.query(MessageSource).filter(
            MessageSource.name == 'stellenbosch_policy_lab'
        ).first()

        if not source:
            logger.error("消息源 'stellenbosch_policy_lab' 未找到，请先执行register.sql")
            return

        config = {
            'id': source.id,
            'mysql_table': 'mp_stellenbosch_messages',
            'chroma_collection': 'stellenbosch_policy_lab',
            'config': {
                'url': 'https://policyinnovationlab.sun.ac.za/news/',
                'region': 'ZA',
                'language': 'en',
            },
            'interval': 86400
        }

    logger.info("=" * 60)
    logger.info("开始测试Stellenbosch采集器")
    logger.info("=" * 60)

    # 创建采集器实例
    collector = StellenboschCollector(config)

    # 初始化
    if not await collector.initialize():
        logger.error("采集器初始化失败")
        return

    # 执行一次采集
    logger.info("执行首次采集...")
    await collector._collect_once()

    # 统计结果
    with create_session() as db:
        total_count = db.query(StellenboschMessage).filter(
            StellenboschMessage.source_id == config['id']
        ).count()
        logger.info(f"数据库中共有 {total_count} 条记录")

        # 显示最新5条记录
        latest_records = db.query(StellenboschMessage).filter(
            StellenboschMessage.source_id == config['id']
        ).order_by(StellenboschMessage.crawled_at.desc()).limit(5).all()

        logger.info("\n最新5条记录:")
        logger.info("-" * 60)
        for idx, record in enumerate(latest_records, 1):
            logger.info(f"{idx}. {record.title[:50]}...")
            logger.info(f"   URL: {record.url}")
            logger.info(f"   发布时间: {record.published_at}")
            logger.info(f"   抓取时间: {record.crawled_at}")
            logger.info(f"   内容长度: {len(record.content)} 字符")
            logger.info(f"   摘要长度: {len(record.summary) if record.summary else 0} 字符")
            logger.info("")

    # 测试增量更新
    logger.info("=" * 60)
    logger.info("测试增量更新（应该不会采集到新数据）")
    logger.info("=" * 60)
    await collector._collect_once()

    with create_session() as db:
        new_total_count = db.query(StellenboschMessage).filter(
            StellenboschMessage.source_id == config['id']
        ).count()
        logger.info(f"增量更新后数据库记录数: {new_total_count}")
        if new_total_count == total_count:
            logger.info("✓ 增量更新测试通过：未采集到重复数据")
        else:
            logger.warning(f"⚠ 增量更新发现 {new_total_count - total_count} 条新记录")

    # 关闭采集器
    await collector.stop()

    logger.info("=" * 60)
    logger.info("测试完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_collector())
