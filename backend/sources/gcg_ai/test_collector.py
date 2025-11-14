# -*- coding: utf-8 -*-

"""
GCG采集器测试脚本
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.sources.gcg_ai.collector import GCGAICollector
from backend.database.connection import create_session
from backend.database.entities import GCGAIMessage

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_collector():
    """测试采集器"""

    # 从数据库获取配置
    with create_session() as db:
        from backend.database.entities import MessageSource
        source = db.query(MessageSource).filter(
            MessageSource.name == 'gcg_ai'
        ).first()

        if not source:
            logger.error("消息源 'gcg_ai' 未找到，请先执行注册脚本")
            return

        config = {
            'id': source.id,
            'mysql_table': source.config.get('mysql_table'),
            'chroma_collection': source.config.get('chroma_collection'),
            'interval': source.config.get('interval', 604800),
            'config': source.config
        }

    logger.info(f"配置: {config}")

    # 创建采集器
    collector = GCGAICollector(config)

    # 初始化
    if not await collector.initialize():
        logger.error("采集器初始化失败")
        return

    logger.info("采集器初始化成功")

    # 执行一次采集
    await collector._collect_once()

    # 检查数据库
    with create_session() as db:
        count = db.query(GCGAIMessage).filter(
            GCGAIMessage.source_id == source.id
        ).count()
        logger.info(f"数据库中共有 {count} 条记录")

        if count > 0:
            latest = db.query(GCGAIMessage).filter(
                GCGAIMessage.source_id == source.id
            ).order_by(
                GCGAIMessage.published_at.desc()
            ).first()

            logger.info(f"最新记录:")
            logger.info(f"  标题: {latest.title}")
            logger.info(f"  URL: {latest.url}")
            logger.info(f"  发布时间: {latest.published_at}")
            logger.info(f"  摘要长度: {len(latest.summary) if latest.summary else 0} 字符")

    # 再次采集，测试去重
    logger.info("\n========== 测试去重机制 ==========")
    await collector._collect_once()

    with create_session() as db:
        new_count = db.query(GCGAIMessage).filter(
            GCGAIMessage.source_id == source.id
        ).count()
        logger.info(f"第二次采集后数据库中共有 {new_count} 条记录")
        logger.info(f"去重是否生效: {'是' if new_count == count else '否（有重复）'}")

    # 关闭浏览器
    await collector.stop()

    logger.info("测试完成")


if __name__ == "__main__":
    asyncio.run(test_collector())
