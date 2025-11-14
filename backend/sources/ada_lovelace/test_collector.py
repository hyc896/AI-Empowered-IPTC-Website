# -*- coding: utf-8 -*-

"""
Ada Lovelace Institute Collector 测试脚本
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.sources.ada_lovelace.collector import AdaLovelaceCollector
from backend.database.connection import create_session
from backend.database.entities import AdaLovelaceMessage

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def test_collector():
    """测试采集器"""
    # 配置
    config = {
        'id': 'e10784ed-bf21-11f0-8cb6-00ff40160484',  # 从数据库查询得到的ID
        'mysql_table': 'mp_ada_lovelace_messages',
        'chroma_collection': 'ada_lovelace',
        'test_mode': True,  # 启用测试模式
        'test_limit': 3,  # 限制采集3篇文章
        'config': {
            'url': 'https://www.adalovelaceinstitute.org/blog/',
            'region': 'UK',
            'language': 'en'
        }
    }

    # 创建采集器
    collector = AdaLovelaceCollector(config)

    try:
        # 初始化
        logger.info("正在初始化采集器...")
        if not await collector.initialize():
            logger.error("采集器初始化失败")
            return

        # 执行单次采集
        logger.info("开始采集...")
        await collector._collect_once()

        # 查询数据库验证结果
        logger.info("查询数据库验证结果...")
        with create_session() as db:
            count = db.query(AdaLovelaceMessage).count()
            logger.info(f"数据库中共有 {count} 条记录")

            if count > 0:
                latest = db.query(AdaLovelaceMessage).order_by(
                    AdaLovelaceMessage.crawled_at.desc()
                ).first()
                logger.info(f"最新记录: {latest.title}")
                logger.info(f"URL: {latest.url}")
                logger.info(f"作者: {latest.provider}")
                logger.info(f"发布时间: {latest.published_at}")
                logger.info(f"摘要长度: {len(latest.summary) if latest.summary else 0} 字符")
                logger.info(f"内容长度: {len(latest.content) if latest.content else 0} 字符")

        logger.info("采集测试完成")

    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
    finally:
        await collector.stop()


if __name__ == "__main__":
    # Windows环境需要设置事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(test_collector())
