# -*- coding: utf-8 -*-

"""
VentureBeat采集器修复验证脚本

验证内容：
1. 流式处理架构是否生效（分批处理）
2. 429错误是否消失
3. 单条失败是否阻塞整体
4. 日志是否清晰展示处理进度
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.sources.venturebeat.collector import VentureBeatCollector
from backend.database.connection import create_session
from backend.database.entities import MessageSource

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_venturebeat_collector():
    """测试VentureBeat采集器（修复后）"""

    # 1. 获取消息源配置
    with create_session() as db:
        source = db.query(MessageSource).filter(
            MessageSource.name.like('%VentureBeat%')
        ).first()

        if not source:
            logger.error("未找到VentureBeat消息源配置")
            return

        logger.info(f"找到消息源: {source.name}")

        config = {
            'id': source.id,
            'interval': source.schedule or '0 0 * * *',
            'mysql_table': source.config.get('mysql_table'),
            'chroma_collection': source.config.get('chroma_collection'),
            'config': source.config
        }

    # 2. 初始化采集器
    logger.info("初始化VentureBeat采集器...")
    collector = VentureBeatCollector(config)

    if not await collector.initialize():
        logger.error("采集器初始化失败")
        return

    # 3. 执行单次采集（观察日志）
    logger.info("开始测试采集（观察日志中的批次处理）...")
    try:
        await collector._collect_once()
        logger.info("采集测试完成")
    except Exception as e:
        logger.error(f"采集测试失败: {e}", exc_info=True)
    finally:
        await collector.stop()


if __name__ == '__main__':
    asyncio.run(test_venturebeat_collector())
