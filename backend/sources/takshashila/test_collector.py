# -*- coding: utf-8 -*-

"""
Takshashila Institution采集器测试脚本
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.sources.takshashila.collector import TakshashilaCollector
from backend.database.connection import create_session
from backend.database.entities import TakshashilaMessage

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_collector():
    """测试采集器"""
    # 查询数据库获取消息源配置
    with create_session() as db:
        from backend.database.entities import MessageSource
        source = db.query(MessageSource).filter(
            MessageSource.name == 'takshashila'
        ).first()

        if not source:
            logger.error("未找到takshashila消息源配置，请先执行register.sql")
            return

        logger.info(f"找到消息源: {source.display_name} (ID: {source.id})")

        # 构建配置
        config = {
            'id': source.id,
            'mysql_table': source.config.get('mysql_table', 'mp_takshashila_messages'),
            'chroma_collection': source.config.get('chroma_collection', 'takshashila'),
            'interval': source.config.get('interval', 86400),
            'config': source.config
        }

    # 创建采集器
    collector = TakshashilaCollector(config)

    try:
        # 初始化
        logger.info("初始化采集器...")
        if not await collector.initialize():
            logger.error("采集器初始化失败")
            return

        # 执行一次采集
        logger.info("开始测试采集...")
        await collector._collect_once()

        # 查询采集结果
        with create_session() as db:
            count = db.query(TakshashilaMessage).filter(
                TakshashilaMessage.source_id == source.id
            ).count()
            logger.info(f"数据库中共有 {count} 条Takshashila记录")

            # 显示最新的5条记录
            latest_records = db.query(TakshashilaMessage).filter(
                TakshashilaMessage.source_id == source.id
            ).order_by(
                TakshashilaMessage.published_at.desc()
            ).limit(5).all()

            logger.info("最新5条记录:")
            for idx, record in enumerate(latest_records, 1):
                logger.info(f"{idx}. [{record.published_at}] {record.title[:50]}...")
                logger.info(f"   URL: {record.url}")
                logger.info(f"   作者: {record.provider}")
                logger.info(f"   类型: {record.publication_type}")
                logger.info(f"   内容长度: {len(record.content)} 字符")
                logger.info(f"   摘要长度: {len(record.summary or '')} 字符")
                logger.info("")

    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
    finally:
        await collector.stop()


if __name__ == "__main__":
    asyncio.run(test_collector())
