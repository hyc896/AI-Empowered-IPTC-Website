# -*- coding: utf-8 -*-

"""
证券时报采集器测试脚本

使用方法：
    python -m backend.sources.securities_times.test_collector

测试场景：
1. 第一次运行：采集N条新记录，验证数据提取和入库
2. 第二次运行：验证滑动去重（遇到已存在记录立即停止，不重复采集）
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.sources.securities_times.collector import SecuritiesTimesCollector
from backend.database.connection import create_session
from backend.database.entities import SecuritiesTimesMessage

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_collector():
    """测试证券时报采集器"""

    # 模拟配置
    config = {
        'id': 'cd1acf31-c48b-11f0-b75e-08bfb82ee112',  # 从数据库注册的UUID
        'config': {
            'interval': 86400,
            'mysql_table': 'mp_securities_times_messages',
            'chroma_collection': 'securities_times',
            'categories': ['yw'],
            'region': 'CN',
            'language': 'zh'
        }
    }

    # 查询当前数据库记录数
    logger.info("=" * 80)
    logger.info("测试前数据库状态")
    logger.info("=" * 80)

    with create_session() as db:
        before_count = db.query(SecuritiesTimesMessage).count()
        latest = db.query(SecuritiesTimesMessage).order_by(
            SecuritiesTimesMessage.published_at.desc()
        ).first()

        logger.info(f"数据库现有记录数: {before_count}")
        if latest:
            logger.info(f"最新记录标题: {latest.title}")
            logger.info(f"最新记录URL: {latest.url}")
            logger.info(f"最新记录发布时间: {latest.published_at}")
        else:
            logger.info("数据库为空，这是首次采集")

    # 创建采集器实例
    collector = SecuritiesTimesCollector(config)

    # 初始化采集器
    logger.info("\n" + "=" * 80)
    logger.info("初始化采集器")
    logger.info("=" * 80)

    if not await collector.initialize():
        logger.error("采集器初始化失败")
        return

    # 执行单次采集
    logger.info("\n" + "=" * 80)
    logger.info("开始采集")
    logger.info("=" * 80)

    try:
        await collector._collect_once()
    except Exception as e:
        logger.error(f"采集失败: {e}", exc_info=True)
    finally:
        await collector.stop()

    # 查询采集后的数据库状态
    logger.info("\n" + "=" * 80)
    logger.info("测试后数据库状态")
    logger.info("=" * 80)

    with create_session() as db:
        after_count = db.query(SecuritiesTimesMessage).count()
        new_count = after_count - before_count

        logger.info(f"数据库现有记录数: {after_count}")
        logger.info(f"本次新增记录数: {new_count}")

        if new_count > 0:
            logger.info("\n最新采集的5条记录：")
            latest_messages = db.query(SecuritiesTimesMessage).order_by(
                SecuritiesTimesMessage.crawled_at.desc()
            ).limit(5).all()

            for idx, msg in enumerate(latest_messages, 1):
                logger.info(f"\n[{idx}] {msg.title}")
                logger.info(f"    URL: {msg.url}")
                logger.info(f"    外部ID: {msg.external_id}")
                logger.info(f"    发布时间: {msg.published_at}")
                logger.info(f"    作者: {msg.provider}")
                logger.info(f"    地区: {msg.region}")
                logger.info(f"    行业标签: {msg.industry_tags}")
                logger.info(f"    AI标签: {msg.ai_tag}")
                logger.info(f"    摘要长度: {len(msg.summary) if msg.summary else 0}")
                logger.info(f"    内容长度: {len(msg.content) if msg.content else 0}")
        else:
            logger.info("⚠ 没有新增记录（可能遇到重复，停止采集）")

    logger.info("\n" + "=" * 80)
    logger.info("测试完成")
    logger.info("=" * 80)
    logger.info("\n建议：")
    logger.info("1. 如果是首次运行且有新增记录，请再次运行本脚本验证去重机制")
    logger.info("2. 第二次运行应该显示'遇到已存储URL，停止采集'")
    logger.info("3. 检查region、industry_tags、ai_tag是否正确填充")


if __name__ == '__main__':
    asyncio.run(test_collector())
