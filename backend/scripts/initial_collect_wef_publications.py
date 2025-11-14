# -*- coding: utf-8 -*-

"""
WEF Publications Initial Collection Script
世界经济论坛AI出版物初始采集脚本

用于首次采集历史数据，需要手动运行。
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Windows环境需要设置事件循环策略
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from backend.config import ConfigManager
from backend.database.connection import create_session
from backend.database.entities import MessageSource
from backend.storage import initialize_chromadb
from backend.llm import GlobalLLMManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_llm_clients():
    """初始化LLM客户端"""
    try:
        # 加载配置
        config_manager = ConfigManager()
        config = config_manager.config

        # 初始化ChromaDB
        chroma_config = config.get('chromadb', {})
        initialize_chromadb(chroma_config)
        logger.info("ChromaDB初始化成功")

        # 初始化LLM GlobalLLMManager
        llm_config = config.get('llm', {})
        embedding_config = llm_config.get('embedding', {})
        GlobalLLMManager.initialize(
            provider=embedding_config.get('provider', 'deepseek'),
            model=embedding_config.get('model', 'deepseek-chat'),
            api_key=embedding_config.get('api_key', ''),
            base_url=embedding_config.get('base_url')
        )
        logger.info("LLM GlobalLLMManager初始化成功")

    except Exception as e:
        logger.error(f"初始化失败: {e}", exc_info=True)
        raise


async def main():
    """主函数"""
    try:
        logger.info("=" * 60)
        logger.info("WEF Publications 初始采集脚本")
        logger.info("=" * 60)

        # 初始化依赖
        init_llm_clients()

        # 查询消息源配置
        with create_session() as db:
            source = db.query(MessageSource).filter(
                MessageSource.name == 'wef_publications'
            ).first()

            if not source:
                logger.error("未找到WEF Publications消息源配置")
                return

            logger.info(f"找到消息源: {source.display_name}")
            logger.info(f"Source ID: {source.id}")

        # 导入采集器
        from backend.sources.wef_publications.collector import WEFPublicationsCollector

        # 构建采集器配置
        collector_config = {
            'id': source.id,
            'interval': source.config.get('interval', 86400),
            'mysql_table': source.config.get('mysql_table'),
            'chroma_collection': source.config.get('chroma_collection'),
            'config': source.config
        }

        # 创建采集器实例
        collector = WEFPublicationsCollector(collector_config)

        # 初始化采集器
        if not await collector.initialize():
            logger.error("采集器初始化失败")
            return

        logger.info("开始采集WEF AI出版物...")

        # 执行一次采集
        await collector._collect_once()

        logger.info("采集完成！")

        # 关闭浏览器
        await collector._close_browser()

        # 统计结果
        with create_session() as db:
            from backend.database.entities import WEFPublicationMessage
            total_count = db.query(WEFPublicationMessage).filter(
                WEFPublicationMessage.source_id == source.id
            ).count()
            logger.info(f"数据库中共有 {total_count} 条WEF出版物记录")

    except Exception as e:
        logger.error(f"采集失败: {e}", exc_info=True)


if __name__ == '__main__':
    asyncio.run(main())
