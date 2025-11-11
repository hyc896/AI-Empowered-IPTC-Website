# -*- coding: utf-8 -*-

"""
CSET采集器测试脚本
用于独立测试CSET采集器功能
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 切换到项目根目录（确保能找到config.yaml）
os.chdir(project_root)

from backend.sources.cset.collector import CSETCollector
from backend.database.entities import CSETMessage

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_cset_collector():
    """测试CSET采集器"""

    # 模拟配置（从数据库读取到的配置）
    config = {
        'id': '4097d1b1-bef5-11f0-8cb6-00ff40160484',  # 从数据库中获取的实际ID
        'name': 'cset',
        'display_name': 'CSET - Center for Security and Emerging Technology',
        'mysql_table': 'mp_cset_messages',
        'chroma_collection': 'cset_messages',
        'config': {
            'url': 'https://cset.georgetown.edu/publications/?fwp_topic=cyberai',
            'region': 'US',
            'timezone': 'America/New_York',
            'language': 'en',
            'interval': 86400
        }
    }

    try:
        # 创建采集器实例
        logger.info("=" * 80)
        logger.info("开始测试CSET采集器")
        logger.info("=" * 80)

        collector = CSETCollector(config)

        # 初始化采集器
        logger.info("\n[1/3] 初始化采集器...")
        init_success = await collector.initialize()
        if not init_success:
            logger.error("采集器初始化失败")
            return

        logger.info("✓ 采集器初始化成功")

        # 执行单次采集
        logger.info("\n[2/3] 执行采集...")
        await collector._collect_once()

        # 查询数据库验证结果
        logger.info("\n[3/3] 验证采集结果...")
        from backend.database.connection import create_session

        with create_session() as db:
            count = db.query(CSETMessage).filter(
                CSETMessage.source_id == config['id']
            ).count()

            logger.info(f"✓ 数据库中共有 {count} 条CSET消息")

            if count > 0:
                # 显示最新的3条记录
                latest_messages = db.query(CSETMessage).filter(
                    CSETMessage.source_id == config['id']
                ).order_by(
                    CSETMessage.published_at.desc()
                ).limit(3).all()

                logger.info("\n最新的3条记录：")
                for idx, msg in enumerate(latest_messages, 1):
                    logger.info(f"\n  [{idx}] {msg.title}")
                    logger.info(f"      作者: {msg.provider or 'N/A'}")
                    logger.info(f"      日期: {msg.published_at}")
                    logger.info(f"      URL: {msg.url}")
                    logger.info(f"      类型: {msg.category}")
                    logger.info(f"      摘要: {msg.summary[:100] if msg.summary else 'N/A'}...")

        # 关闭浏览器
        await collector._close_browser()

        logger.info("\n" + "=" * 80)
        logger.info("✓ 测试完成")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)


if __name__ == "__main__":
    # Windows环境需要设置事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(test_cset_collector())
