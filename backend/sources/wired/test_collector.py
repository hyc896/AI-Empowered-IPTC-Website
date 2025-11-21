# -*- coding: utf-8 -*-

"""
Wired采集器测试脚本

测试内容：
1. RSS Feed解析
2. 数据库插入
3. 去重机制验证
4. 字段映射验证
"""

import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.connection import create_session
from backend.database.entities import WiredMessage
from backend.sources.wired.collector import WiredCollector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_collector():
    """测试Wired采集器"""

    # 1. 从数据库读取配置
    with create_session() as db:
        from backend.database.entities import MessageSource
        source = db.query(MessageSource).filter(
            MessageSource.name == 'Wired'
        ).first()

        if not source:
            logger.error("未找到Wired消息源配置")
            return

        config = {
            'id': source.id,
            'interval': 3600,
            'config': source.config
        }

    logger.info(f"消息源配置: {config}")

    # 2. 创建采集器实例
    collector = WiredCollector(config)

    # 3. 初始化
    if not await collector.initialize():
        logger.error("采集器初始化失败")
        return

    logger.info("采集器初始化成功")

    # 4. 查询采集前的数据量
    with create_session() as db:
        before_count = db.query(WiredMessage).filter(
            WiredMessage.source_id == source.id
        ).count()

    logger.info(f"采集前数据量: {before_count}")

    # 5. 执行一次采集
    logger.info("开始采集...")
    await collector._collect_once()

    # 6. 查询采集后的数据量
    with create_session() as db:
        after_count = db.query(WiredMessage).filter(
            WiredMessage.source_id == source.id
        ).count()

    logger.info(f"采集后数据量: {after_count}")
    logger.info(f"新增记录数: {after_count - before_count}")

    # 7. 显示最新的5条记录
    with create_session() as db:
        latest_messages = db.query(WiredMessage).filter(
            WiredMessage.source_id == source.id
        ).order_by(
            WiredMessage.published_at.desc()
        ).limit(5).all()

        logger.info("\n最新5条记录：")
        for i, msg in enumerate(latest_messages, 1):
            logger.info(f"\n[{i}] {msg.title}")
            logger.info(f"    URL: {msg.url}")
            logger.info(f"    Provider: {msg.provider}")
            logger.info(f"    Published: {msg.published_at}")
            logger.info(f"    Region: {msg.region}")
            logger.info(f"    Industry Tags: {msg.industry_tags}")
            logger.info(f"    AI Tag: {msg.ai_tag}")
            logger.info(f"    Content Length: {len(msg.content) if msg.content else 0}")
            logger.info(f"    Summary Length: {len(msg.summary) if msg.summary else 0}")

    # 8. 测试去重：再次执行采集
    logger.info("\n\n测试去重机制（第二次采集）...")
    await collector._collect_once()

    # 9. 验证数据量未增加
    with create_session() as db:
        final_count = db.query(WiredMessage).filter(
            WiredMessage.source_id == source.id
        ).count()

    logger.info(f"第二次采集后数据量: {final_count}")

    if final_count == after_count:
        logger.info("✅ 去重机制工作正常：第二次采集未重复插入数据")
    else:
        logger.warning(f"⚠️  去重机制可能有问题：数据量从 {after_count} 变为 {final_count}")


if __name__ == "__main__":
    asyncio.run(test_collector())
