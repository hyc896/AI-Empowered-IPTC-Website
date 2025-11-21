# -*- coding: utf-8 -*-

"""
Times of India采集器测试脚本
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.sources.times_of_india.collector import TimesOfIndiaCollector
from backend.database.connection import create_session
from backend.database.entities import TimesOfIndiaMessage

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_collector():
    """测试采集器"""

    # 从数据库获取消息源配置
    with create_session() as db:
        from backend.database.entities import MessageSource
        source = db.query(MessageSource).filter(
            MessageSource.name == 'Times of India Tech'
        ).first()

        if not source:
            logger.error("未找到消息源配置，请先执行register.sql")
            return

        config = {
            'id': source.id,
            'name': source.name,
            'interval': 3600,
            'config': source.config
        }

        logger.info(f"消息源配置: {config}")

    # 创建采集器
    collector = TimesOfIndiaCollector(config)

    # 初始化
    if not await collector.initialize():
        logger.error("采集器初始化失败")
        return

    # 执行一次采集
    logger.info("开始测试采集...")
    await collector._collect_once()

    # 查询数据库验证结果
    with create_session() as db:
        count = db.query(TimesOfIndiaMessage).filter(
            TimesOfIndiaMessage.source_id == config['id']
        ).count()

        logger.info(f"\n{'='*80}")
        logger.info(f"采集结果统计：")
        logger.info(f"  数据库记录总数: {count}")

        # 显示最新的3条记录
        latest = db.query(TimesOfIndiaMessage).filter(
            TimesOfIndiaMessage.source_id == config['id']
        ).order_by(
            TimesOfIndiaMessage.published_at.desc()
        ).limit(3).all()

        logger.info(f"\n最新记录示例（前3条）：")
        for i, msg in enumerate(latest, 1):
            logger.info(f"\n[{i}] {msg.title}")
            logger.info(f"  URL: {msg.url}")
            logger.info(f"  发布时间: {msg.published_at}")
            logger.info(f"  内容长度: {len(msg.content)} 字符")
            logger.info(f"  摘要长度: {len(msg.summary) if msg.summary else 0} 字符")
            logger.info(f"  地区: {msg.region}")
            logger.info(f"  行业标签: {msg.industry_tags}")
            logger.info(f"  AI标签: {msg.ai_tag}")
            logger.info(f"  分类: {msg.category}")
            logger.info(f"  语言: {msg.language}")

        logger.info(f"\n{'='*80}")


if __name__ == '__main__':
    asyncio.run(test_collector())
