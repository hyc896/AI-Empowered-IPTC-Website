# -*- coding: utf-8 -*-

"""
Inteligencia Argentina Collector测试脚本

使用方法：
python -m backend.sources.inteligencia_argentina.test_collector
"""

import asyncio
import logging
from backend.database.connection import create_session
from backend.database.entities import MessageSource, InteligenciaArgentinaMessage
from backend.sources.inteligencia_argentina.collector import InteligenciaArgentinaCollector
from backend.services.browser_pool import BrowserPool

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_collector():
    """测试采集器"""
    browser_pool = None

    try:
        # 1. 从数据库加载消息源配置
        logger.info("【测试】加载消息源配置...")
        with create_session() as db:
            source = db.query(MessageSource).filter(
                MessageSource.name == 'Inteligencia Argentina AI'
            ).first()

            if not source:
                logger.error("【测试】消息源未注册，请先执行register.sql")
                return

            config = {
                'id': source.id,
                'name': source.name,
                'config': source.config,
                'interval': source.config.get('interval', 3600),
            }

        logger.info(f"【测试】消息源ID: {config['id']}")
        logger.info(f"【测试】采集间隔: {config['interval']}秒")

        # 2. 创建浏览器池
        logger.info("【测试】初始化浏览器池...")
        browser_pool = BrowserPool(config={
            'min_size': 0,
            'max_size': 3,
            'init_size': 1,
            'headless': True
        })
        await browser_pool.initialize()

        # 3. 创建采集器
        logger.info("【测试】创建采集器...")
        collector = InteligenciaArgentinaCollector(config)
        collector.set_browser_pool(browser_pool)

        # 4. 初始化采集器
        logger.info("【测试】初始化采集器...")
        if not await collector.initialize():
            logger.error("【测试】采集器初始化失败")
            return

        # 5. 执行采集
        logger.info("【测试】开始采集...")
        try:
            await collector._collect_once()
        except Exception as e:
            logger.error(f"【测试】采集失败: {e}", exc_info=True)

        # 6. 检查采集结果
        logger.info("【测试】检查采集结果...")
        with create_session() as db:
            count = db.query(InteligenciaArgentinaMessage).filter(
                InteligenciaArgentinaMessage.source_id == config['id']
            ).count()

            logger.info(f"【测试】数据库中共有 {count} 条记录")

            if count > 0:
                # 显示最新5条
                latest = db.query(InteligenciaArgentinaMessage).filter(
                    InteligenciaArgentinaMessage.source_id == config['id']
                ).order_by(InteligenciaArgentinaMessage.crawled_at.desc()).limit(5).all()

                logger.info("\n【测试】最新5条记录：")
                for idx, msg in enumerate(latest, 1):
                    logger.info(f"  {idx}. {msg.title}")
                    logger.info(f"     URL: {msg.url}")
                    logger.info(f"     发布时间: {msg.published_at}")
                    logger.info(f"     地区: {msg.region}")
                    logger.info(f"     行业标签: {msg.industry_tags}")
                    logger.info(f"     AI标签: {msg.ai_tag}")
                    logger.info(f"     摘要长度: {len(msg.summary or '')} 字符")
                    logger.info("")

        logger.info("【测试】采集完成！")

    except Exception as e:
        logger.error(f"【测试】异常: {e}", exc_info=True)

    finally:
        # 清理浏览器池
        if browser_pool:
            logger.info("【测试】关闭浏览器池...")
            await browser_pool.close()


if __name__ == '__main__':
    asyncio.run(test_collector())
