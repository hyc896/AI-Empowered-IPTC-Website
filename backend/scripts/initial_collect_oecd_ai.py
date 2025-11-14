# -*- coding: utf-8 -*-

"""
OECD AI Policy Observatory Initial Collection Script
OECD人工智能政策观察站初始采集脚本 - 一次性收集所有历史数据

使用方法：
python backend/scripts/initial_collect_oecd_ai.py

功能：
- 访问每篇文章的详情页提取完整内容
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

from backend.config import ConfigManager
from backend.database.connection import create_session
from backend.database.entities import MessageSource, OECDAIMessage
from backend.sources.oecd_ai.collector import OECDAICollector

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
    config_manager = ConfigManager()
    config_path = project_root / "config.yaml"
    config_manager.load_config(str(config_path))
    config = config_manager

    # 初始化ChromaDB
    try:
        from backend.storage import initialize_chromadb
        chromadb_config = config.get('chromadb', {})
        initialize_chromadb(chromadb_config)
        logger.info("【初始化】ChromaDB初始化成功")
    except Exception as e:
        logger.warning(f"【初始化】ChromaDB初始化失败: {e}")

    # 初始化LLM
    try:
        from backend.llm import GlobalLLMManager
        llm_config = config.get('llm', {})
        embedding_config = llm_config.get('embedding', {})
        fast_config = llm_config.get('fast', {})

        llm_manager = GlobalLLMManager.get_instance()
        llm_manager.initialize_embedding(embedding_config)
        llm_manager.initialize_fast(fast_config)
        logger.info("【初始化】LLM服务初始化成功")
    except Exception as e:
        logger.warning(f"【初始化】LLM服务初始化失败: {e}")

    return config


async def get_oecd_ai_source_config():
    """
    从数据库获取OECD AI消息源配置

    Returns:
        source_config: 消息源配置字典
    """
    try:
        with create_session() as db:
            source = db.query(MessageSource).filter(
                MessageSource.name == 'oecd_ai'
            ).first()

            if not source:
                logger.error("【错误】数据库中未找到OECD AI消息源配置，请先执行register.sql")
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


async def collect_all_historical_data(collector: OECDAICollector):
    """
    采集所有历史数据

    Args:
        collector: OECD AI采集器实例
    """
    logger.info("【开始】采集所有历史文章...")

    try:
        # 调用采集器的单次采集方法
        # OECD AI网站列表页显示最近的文章
        # 直接调用_collect_once()即可获取所有显示的文章
        await collector._collect_once()

        # 统计采集结果
        with create_session() as db:
            total_count = db.query(OECDAIMessage).filter(
                OECDAIMessage.source_id == collector.source_id
            ).count()

            logger.info(f"【完成】采集完成！数据库中共有 {total_count} 篇文章")

    except Exception as e:
        logger.error(f"【错误】采集失败: {e}", exc_info=True)


async def main():
    """主函数"""
    logger.info("="*80)
    logger.info("OECD AI初始采集脚本 - 开始执行")
    logger.info("="*80)

    # 1. 初始化依赖
    config = await initialize_dependencies()

    # 2. 获取消息源配置
    source_config = await get_oecd_ai_source_config()
    if not source_config:
        logger.error("【失败】无法获取消息源配置，退出")
        return

    # 3. 创建采集器实例
    logger.info("【初始化】创建OECD AI采集器...")
    collector = OECDAICollector(source_config)

    # 4. 初始化采集器（启动浏览器）
    if not await collector.initialize():
        logger.error("【失败】采集器初始化失败，退出")
        return

    # 5. 采集所有历史数据
    await collect_all_historical_data(collector)

    # 6. 停止采集器
    await collector.stop()

    logger.info("="*80)
    logger.info("OECD AI初始采集脚本 - 执行完成")
    logger.info("="*80)


if __name__ == '__main__':
    asyncio.run(main())
