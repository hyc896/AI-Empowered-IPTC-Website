# -*- coding: utf-8 -*-

"""
CSET采集器简单测试
不依赖LLM和ChromaDB，仅测试网页爬取和数据提取
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# 切换到项目根目录
project_root = Path(__file__).parent.parent.parent.parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))

from backend.sources.cset.collector import CSETCollector
from backend.database.entities import CSETMessage
from backend.database.connection import create_session

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def simple_test():
    """简单测试：爬取、存储、验证"""

    # 使用真实的source_id（从数据库查询）
    with create_session() as db:
        from backend.database.entities import MessageSource
        source = db.query(MessageSource).filter(MessageSource.name == 'cset').first()

        if not source:
            logger.error("未找到CSET消息源，请先执行register.sql")
            return

        source_id = source.id
        logger.info(f"✓ 找到消息源: {source.display_name} (ID: {source_id})")

    # 配置
    config = {
        'id': source_id,
        'name': 'cset',
        'display_name': 'CSET',
        'mysql_table': 'mp_cset_messages',
        'chroma_collection': 'cset_messages',
        'config': {
            'url': 'https://cset.georgetown.edu/publications/?fwp_topic=cyberai',
            'region': 'US',
            'language': 'en'
        }
    }

    try:
        logger.info("\n" + "=" * 80)
        logger.info("第1次采集：获取最新文章")
        logger.info("=" * 80)

        collector = CSETCollector(config)
        await collector.initialize()

        # 第一次采集
        await collector._collect_once()

        # 查询结果
        with create_session() as db:
            count1 = db.query(CSETMessage).filter(CSETMessage.source_id == source_id).count()
            logger.info(f"\n✓ 第1次采集完成，数据库中共 {count1} 条记录")

            if count1 > 0:
                latest = db.query(CSETMessage).filter(
                    CSETMessage.source_id == source_id
                ).order_by(CSETMessage.published_at.desc()).first()

                logger.info(f"\n最新文章:")
                logger.info(f"  标题: {latest.title}")
                logger.info(f"  作者: {latest.provider or 'N/A'}")
                logger.info(f"  日期: {latest.published_at}")
                logger.info(f"  类型: {latest.category}")
                logger.info(f"  URL: {latest.url}")

        # 第二次采集（测试去重）
        logger.info("\n" + "=" * 80)
        logger.info("第2次采集：测试去重功能")
        logger.info("=" * 80)

        await collector._collect_once()

        # 验证去重
        with create_session() as db:
            count2 = db.query(CSETMessage).filter(CSETMessage.source_id == source_id).count()
            logger.info(f"\n✓ 第2次采集完成，数据库中共 {count2} 条记录")

            if count1 == count2:
                logger.info("✓ 去重功能正常：第2次采集未产生重复数据")
            else:
                logger.warning(f"⚠ 可能存在重复：记录数从 {count1} 增加到 {count2}")

        await collector._close_browser()

        logger.info("\n" + "=" * 80)
        logger.info("✓ 测试完成")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(simple_test())
