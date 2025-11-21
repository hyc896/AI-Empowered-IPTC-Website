# -*- coding: utf-8 -*-

"""
CNBC Technology Collector Test Script
测试CNBC科技新闻采集器
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.sources.cnbc.collector import CNBCCollector
from backend.database.connection import create_session
from backend.database.entities import CNBCMessage

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def test_collector():
    """测试CNBC采集器"""

    # 从数据库获取配置
    with create_session() as db:
        from backend.database.entities import MessageSource
        source = db.query(MessageSource).filter(
            MessageSource.name == 'CNBC Technology'
        ).first()

        if not source:
            logger.error("未找到CNBC Technology消息源配置")
            return

        config = {
            'id': source.id,
            'interval': 3600,
            'config': source.config
        }

        logger.info(f"消息源配置: {config}")

    # 创建采集器实例
    collector = CNBCCollector(config)

    # 初始化
    if not await collector.initialize():
        logger.error("采集器初始化失败")
        return

    # 检查数据库现有记录数
    with create_session() as db:
        before_count = db.query(CNBCMessage).filter(
            CNBCMessage.source_id == config['id']
        ).count()
        logger.info(f"采集前数据库记录数: {before_count}")

    # 执行一次采集
    logger.info("=" * 80)
    logger.info("开始测试采集...")
    logger.info("=" * 80)

    await collector._collect_once()

    # 检查采集后记录数
    with create_session() as db:
        after_count = db.query(CNBCMessage).filter(
            CNBCMessage.source_id == config['id']
        ).count()
        new_count = after_count - before_count

        logger.info("=" * 80)
        logger.info(f"采集完成! 采集前: {before_count}, 采集后: {after_count}, 新增: {new_count}")
        logger.info("=" * 80)

        # 显示最新的3条记录
        latest_messages = db.query(CNBCMessage).filter(
            CNBCMessage.source_id == config['id']
        ).order_by(
            CNBCMessage.published_at.desc()
        ).limit(3).all()

        logger.info("\n最新3条记录:")
        for i, msg in enumerate(latest_messages, 1):
            logger.info(f"\n记录 {i}:")
            logger.info(f"  标题: {msg.title}")
            logger.info(f"  URL: {msg.url}")
            logger.info(f"  发布时间: {msg.published_at}")
            logger.info(f"  地区: {msg.region}")
            logger.info(f"  行业标签: {msg.industry_tags}")
            logger.info(f"  AI标签: {msg.ai_tag}")
            logger.info(f"  摘要长度: {len(msg.summary) if msg.summary else 0}")


if __name__ == '__main__':
    asyncio.run(test_collector())
