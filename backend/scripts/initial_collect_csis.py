# -*- coding: utf-8 -*-

"""
CSIS AI Topic初始采集脚本

功能：
- 一次性采集所有历史文章（332条，分34页）
- 处理分页逻辑（Drupal Views AJAX分页）
- 访问每篇文章详情页获取完整内容
- 存储到MySQL + ChromaDB

执行方式：
python backend/scripts/initial_collect_csis.py
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime

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
from backend.sources.csis.collector import CSISCollector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('csis_initial_collect.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def init_llm_clients():
    """初始化LLM客户端（包括翻译器和embedding）"""
    try:
        config_manager = ConfigManager()
        config = config_manager.load_config()

        # 初始化ChromaDB
        chroma_config = config.get('chromadb', {})
        initialize_chromadb(chroma_config)

        # 初始化LLM GlobalManager
        embedding_config = config.get('llm', {}).get('embedding', {})
        if not embedding_config:
            logger.warning("配置文件中未找到llm.embedding配置")
            return

        GlobalLLMManager.initialize(
            provider=embedding_config.get('provider', 'openai'),
            model=embedding_config.get('model'),
            api_key=embedding_config.get('api_key'),
            base_url=embedding_config.get('base_url')
        )

        logger.info("LLM客户端初始化成功")

    except Exception as e:
        logger.error(f"LLM客户端初始化失败: {e}", exc_info=True)
        raise


async def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("CSIS AI Topic 初始采集任务启动")
    logger.info("=" * 60)

    try:
        # 1. 初始化依赖
        logger.info("[1/5] 初始化依赖...")
        init_llm_clients()

        # 2. 查询消息源配置
        logger.info("[2/5] 查询消息源配置...")
        with create_session() as db:
            source = db.query(MessageSource).filter(
                MessageSource.name == 'csis'
            ).first()

            if not source:
                logger.error("未找到csis消息源配置，请先执行register.sql")
                return

            logger.info(f"消息源ID: {source.id}")
            logger.info(f"消息源名称: {source.display_name}")
            logger.info(f"是否启用: {source.is_active}")

            # 构建配置字典
            source_config = {
                'id': source.id,
                'name': source.name,
                'mysql_table': source.config.get('mysql_table'),
                'chroma_collection': source.config.get('chroma_collection'),
                'interval': source.config.get('interval', 86400),
                'config': source.config
            }

        # 3. 创建采集器实例
        logger.info("[3/5] 创建采集器实例...")
        collector = CSISCollector(source_config)

        # 初始化采集器（启动浏览器）
        if not await collector.initialize():
            logger.error("采集器初始化失败")
            return

        # 4. 执行初始采集
        logger.info("[4/5] 开始采集历史文章...")
        logger.info("注意: CSIS有332条历史文章，预计需要20-30分钟")

        await collector._collect_once()

        # 5. 统计结果
        logger.info("[5/5] 统计采集结果...")
        with create_session() as db:
            total_count = db.query(CSISMessage).filter(
                CSISMessage.source_id == source.id
            ).count()

            latest_article = db.query(CSISMessage).filter(
                CSISMessage.source_id == source.id
            ).order_by(
                CSISMessage.published_at.desc()
            ).first()

            logger.info(f"采集完成！共 {total_count} 篇文章")
            if latest_article:
                logger.info(f"最新文章: {latest_article.title}")
                logger.info(f"发布时间: {latest_article.published_at}")
                logger.info(f"文章链接: {latest_article.url}")

        # 关闭采集器
        await collector.stop()

        logger.info("=" * 60)
        logger.info("CSIS AI Topic 初始采集任务完成")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"初始采集失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Windows环境UTF-8输出支持
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

    asyncio.run(main())
