# -*- coding: utf-8 -*-

"""
Bloomberg Collector Test Script
测试Bloomberg采集器（验证去重机制）
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from backend.sources.bloomberg.collector import BloombergCollector
from backend.database.connection import create_session
from backend.database.entities import BloombergMessage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_collector():
    """测试采集器"""

    config = {
        'id': 'dce23340-c495-11f0-b75e-08bfb82ee112',
        'interval': 3600,
        'config': {
            'mysql_table': 'mp_bloomberg_messages',
            'chroma_collection': 'bloomberg_tech',
            'region': '全球',
            'language': 'en'
        }
    }

    collector = BloombergCollector(config)

    if not await collector.initialize():
        logger.error("采集器初始化失败")
        return

    logger.info("=" * 60)
    logger.info("开始第一次采集（预期：采集N条新记录）")
    logger.info("=" * 60)

    await collector._collect_once()

    with create_session() as db:
        count1 = db.query(BloombergMessage).filter(
            BloombergMessage.source_id == config['id']
        ).count()
        logger.info(f"第一次采集后数据库记录数: {count1}")

    logger.info("=" * 60)
    logger.info("等待5秒后进行第二次采集...")
    logger.info("=" * 60)
    await asyncio.sleep(5)

    logger.info("=" * 60)
    logger.info("开始第二次采集（预期：遇到已存在记录立即停止，无重复采集）")
    logger.info("=" * 60)

    await collector._collect_once()

    with create_session() as db:
        count2 = db.query(BloombergMessage).filter(
            BloombergMessage.source_id == config['id']
        ).count()
        logger.info(f"第二次采集后数据库记录数: {count2}")

        if count1 == count2:
            logger.info("✓ 去重机制验证成功！第二次采集无重复记录")
        else:
            logger.warning(f"⚠ 去重机制可能有问题，记录数从 {count1} 变为 {count2}")

        latest_records = db.query(BloombergMessage).filter(
            BloombergMessage.source_id == config['id']
        ).order_by(
            BloombergMessage.published_at.desc()
        ).limit(3).all()

        logger.info("=" * 60)
        logger.info("最新的3条记录：")
        for idx, record in enumerate(latest_records, 1):
            logger.info(f"{idx}. {record.title[:60]}...")
            logger.info(f"   URL: {record.url}")
            logger.info(f"   发布时间: {record.published_at}")
            logger.info(f"   Region: {record.region}")
            logger.info(f"   Industry Tags: {record.industry_tags}")
            logger.info(f"   AI Tag: {record.ai_tag}")
            logger.info("")


if __name__ == "__main__":
    asyncio.run(test_collector())
