# -*- coding: utf-8 -*-

"""
OBIA采集器测试脚本
"""

import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.sources.obia.collector import OBIACollector
from backend.database.connection import create_session
from backend.database.entities import OBIAMessage

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_collector():
    """测试OBIA采集器"""

    # 从数据库获取消息源配置
    with create_session() as db:
        from backend.database.entities import MessageSource
        source = db.query(MessageSource).filter(MessageSource.name == 'obia').first()

        if not source:
            logger.error("未找到OBIA消息源配置")
            return

        config = {
            'id': source.id,
            'interval': 86400,
            'mysql_table': 'mp_obia_messages',
            'chroma_collection': 'obia_publications',
            'config': {
                'url': 'https://obia.nic.br/s/publicacoes',
                'region': 'BR',
                'language': 'pt'
            }
        }

    logger.info("=== 开始测试OBIA采集器 ===")

    # 创建采集器实例
    collector = OBIACollector(config)

    # 初始化
    if not await collector.initialize():
        logger.error("采集器初始化失败")
        return

    # 执行一次采集
    logger.info("开始采集...")
    await collector._collect_once()

    # 查询数据库验证
    with create_session() as db:
        count = db.query(OBIAMessage).filter(
            OBIAMessage.source_id == config['id']
        ).count()

        logger.info(f"\n=== 采集结果 ===")
        logger.info(f"数据库中共有 {count} 条OBIA出版物记录")

        # 显示最新3条记录
        latest = db.query(OBIAMessage).filter(
            OBIAMessage.source_id == config['id']
        ).order_by(
            OBIAMessage.published_at.desc()
        ).limit(3).all()

        logger.info(f"\n最新3条记录：")
        for idx, msg in enumerate(latest, 1):
            logger.info(f"\n{idx}. {msg.title}")
            logger.info(f"   分类: {msg.category}")
            logger.info(f"   发布时间: {msg.published_at}")
            logger.info(f"   作者: {msg.provider}")
            logger.info(f"   URL: {msg.url}")
            logger.info(f"   摘要长度: {len(msg.summary or '')} 字符")

    await collector.stop()
    logger.info("\n=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(test_collector())
