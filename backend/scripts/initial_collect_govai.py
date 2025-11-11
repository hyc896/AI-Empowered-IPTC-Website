# -*- coding: utf-8 -*-

"""
GovAI Initial Collection Script
GovAI研究论文初始采集脚本 - 一次性收集所有历史数据

使用方法：
python backend/scripts/initial_collect_govai.py

功能：
- 无限滚动直到加载所有历史论文
- 访问每篇论文的列表页提取完整信息
- 手动初始化依赖（ChromaDB、LLM、Config）
- 详细进度日志
"""

import sys
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 设置Windows事件循环策略
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from backend.config import GlobalConfig
from backend.database.connection import create_session
from backend.database.entities import MessageSource, GovAIMessage
from backend.sources.govai.collector import GovAICollector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def initialize_dependencies():
    """
    初始化依赖（ChromaDB、LLM、Config）

    Returns:
        config: 配置对象
    """
    logger.info("【初始化】正在加载配置...")

    from backend.config.config_manager import ConfigManager
    from backend.storage import initialize_chromadb
    from backend.llm.global_llm_manager import GlobalLLMManager

    config_path = project_root / 'config.yaml'
    config_manager = ConfigManager()
    config_manager.load_config(str(config_path))
    config_data = config_manager.get_config()

    # 初始化ChromaDB
    chromadb_config = config_data.get("database", {}).get("chromadb", {})
    if not initialize_chromadb(chromadb_config):
        logger.error("ChromaDB初始化失败")
        return None
    logger.info("✓ ChromaDB初始化成功")

    # 初始化LLM客户端
    llm_config = config_data.get("llm", {})
    embedding_config = llm_config.get("embedding", {})
    fast_config = llm_config.get("fast", {})

    llm_manager = GlobalLLMManager.get_instance()
    llm_manager.initialize(
        chat_config=None,
        embedding_config=embedding_config,
        fast_config=fast_config
    )
    logger.info("✓ LLM客户端初始化成功")

    return config_data


async def get_govai_source_config():
    """
    从数据库获取GovAI消息源配置

    Returns:
        source_config: 消息源配置字典
    """
    try:
        with create_session() as db:
            source = db.query(MessageSource).filter(
                MessageSource.name == 'govai'
            ).first()

            if not source:
                logger.error("【错误】数据库中未找到GovAI消息源配置，请先执行register.sql")
                return None

            source_config = {
                'id': source.id,
                'name': source.name,
                'display_name': source.display_name,
                'mysql_table': source.config.get('mysql_table'),
                'chroma_collection': source.config.get('chroma_collection'),
                'config': source.config,
                'interval': source.config.get('interval', 86400)
            }

            logger.info(f"【配置】消息源: {source.display_name} (ID: {source.id})")
            return source_config

    except Exception as e:
        logger.error(f"【错误】获取消息源配置失败: {e}")
        return None


async def collect_all_historical_data(collector: GovAICollector):
    """
    采集所有历史数据（无限滚动）

    Args:
        collector: GovAI采集器实例
    """
    logger.info("【开始】采集所有历史论文...")

    try:
        # 调用采集器的单次采集方法
        # 由于GovAI网站使用静态HTML，不需要无限滚动
        # 直接调用_collect_once()即可获取所有论文
        await collector._collect_once()

        # 统计采集结果
        with create_session() as db:
            total_count = db.query(GovAIMessage).filter(
                GovAIMessage.source_id == collector.source_id
            ).count()

            logger.info(f"【完成】采集完成！数据库中共有 {total_count} 篇论文")

    except Exception as e:
        logger.error(f"【错误】采集失败: {e}", exc_info=True)


async def main():
    """主函数"""
    logger.info("="*80)
    logger.info("GovAI初始采集脚本 - 开始执行")
    logger.info("="*80)

    # 1. 初始化依赖
    config = await initialize_dependencies()

    # 2. 获取消息源配置
    source_config = await get_govai_source_config()
    if not source_config:
        logger.error("【失败】无法获取消息源配置，退出")
        return

    # 3. 创建采集器实例
    logger.info("【初始化】创建GovAI采集器...")
    collector = GovAICollector(source_config)

    # 4. 初始化采集器（启动浏览器）
    if not await collector.initialize():
        logger.error("【失败】采集器初始化失败，退出")
        return

    # 5. 采集所有历史数据
    await collect_all_historical_data(collector)

    # 6. 停止采集器
    await collector.stop()

    logger.info("="*80)
    logger.info("GovAI初始采集脚本 - 执行完成")
    logger.info("="*80)


if __name__ == '__main__':
    asyncio.run(main())
