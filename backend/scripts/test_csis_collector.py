# -*- coding: utf-8 -*-

"""
CSIS采集器测试脚本
快速验证采集器基本功能
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Windows环境异步支持
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from backend.config.config_manager import ConfigManager
from backend.database.connection import create_session
from backend.database.entities import MessageSource, CSISMessage
from backend.storage import initialize_chromadb
from backend.llm import GlobalLLMManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_llm_clients():
    """初始化LLM客户端"""
    try:
        config_manager = ConfigManager()
        config = config_manager.load_config()

        # 初始化ChromaDB
        chroma_config = config.get('chromadb', {})
        initialize_chromadb(chroma_config)

        # 初始化LLM
        embedding_config = config.get('llm', {}).get('embedding', {})
        if embedding_config:
            GlobalLLMManager.initialize(
                provider=embedding_config.get('provider', 'openai'),
                model=embedding_config.get('model'),
                api_key=embedding_config.get('api_key'),
                base_url=embedding_config.get('base_url')
            )

        logger.info("依赖初始化成功")
    except Exception as e:
        logger.error(f"依赖初始化失败: {e}", exc_info=True)
        raise


async def test_basic_collection():
    """测试基本采集功能"""
    from backend.sources.csis.collector import CSISCollector

    try:
        # 初始化依赖
        logger.info("初始化依赖...")
        init_llm_clients()

        # 查询消息源配置
        logger.info("查询消息源配置...")
        with create_session() as db:
            source = db.query(MessageSource).filter(
                MessageSource.name == 'csis'
            ).first()

            if not source:
                logger.error("未找到csis消息源配置")
                return

            source_config = {
                'id': source.id,
                'name': source.name,
                'mysql_table': source.config.get('mysql_table'),
                'chroma_collection': source.config.get('chroma_collection'),
                'interval': source.config.get('interval', 86400),
                'config': source.config
            }

        # 创建采集器
        logger.info("创建采集器...")
        collector = CSISCollector(source_config)

        if not await collector.initialize():
            logger.error("采集器初始化失败")
            return

        # 执行一次采集
        logger.info("执行测试采集...")
        await collector._collect_once()

        # 检查结果
        logger.info("检查采集结果...")
        with create_session() as db:
            count = db.query(CSISMessage).count()
            logger.info(f"数据库中共有 {count} 篇文章")

            if count > 0:
                latest = db.query(CSISMessage).order_by(
                    CSISMessage.crawled_at.desc()
                ).first()
                logger.info(f"最新文章: {latest.title}")
                logger.info(f"URL: {latest.url}")
                logger.info(f"摘要长度: {len(latest.summary) if latest.summary else 0} 字符")

        # 关闭采集器
        await collector.stop()

        logger.info("测试完成！")

    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Windows环境UTF-8输出支持
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

    asyncio.run(test_basic_collection())
