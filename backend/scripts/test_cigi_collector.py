# -*- coding: utf-8 -*-

"""
CIGI Collector Test Script
CIGI采集器测试脚本

测试功能：
1. 第一次采集：收集最新的5篇文章
2. 第二次采集：验证去重功能（应该0条新文章）
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Windows控制台UTF-8编码支持
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.entities import CIGIMessage, MessageSource
from backend.config import ConfigManager
from backend.storage.chromadb_storage import ChromaDBStorage
from backend.llm import GlobalLLMManager
from backend.sources.cigi.collector import CIGICollector

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_llm_clients(config):
    """初始化LLM客户端"""
    try:
        llm_config = config.get_config().get('llm', {})
        embedding_config = llm_config.get('embedding', {})
        fast_config = llm_config.get('fast', {})

        if not embedding_config or not fast_config:
            logger.error("未找到完整的LLM配置")
            return False

        GlobalLLMManager.initialize(embedding_config, fast_config)
        logger.info("LLM客户端初始化成功")
        return True

    except Exception as e:
        logger.error(f"LLM客户端初始化失败: {e}")
        return False


def initialize_chromadb(config):
    """初始化ChromaDB"""
    try:
        chroma_config = config.get_config().get('chromadb', {})
        host = chroma_config.get('host', 'localhost')
        port = chroma_config.get('port', 8000)

        storage = ChromaDBStorage(host=host, port=port)
        logger.info(f"ChromaDB初始化成功: {host}:{port}")
        return storage

    except Exception as e:
        logger.error(f"ChromaDB初始化失败: {e}")
        return None


async def test_collector_once(collector: CIGICollector, round_num: int):
    """
    测试单次采集

    Args:
        collector: 采集器实例
        round_num: 轮次编号
    """
    logger.info("=" * 60)
    logger.info(f"第 {round_num} 轮采集开始")
    logger.info("=" * 60)

    # 查看当前数据库中的记录数
    from backend.database.connection import create_session
    with create_session() as db:
        count_before = db.query(CIGIMessage).filter(
            CIGIMessage.source_id == collector.source_id
        ).count()
        logger.info(f"采集前数据库中有 {count_before} 条记录")

    # 执行采集
    await collector._collect_once()

    # 查看采集后的记录数
    with create_session() as db:
        count_after = db.query(CIGIMessage).filter(
            CIGIMessage.source_id == collector.source_id
        ).count()
        logger.info(f"采集后数据库中有 {count_after} 条记录")
        logger.info(f"本轮新增 {count_after - count_before} 条记录")

        # 显示最新的几条记录
        latest_messages = db.query(CIGIMessage).filter(
            CIGIMessage.source_id == collector.source_id
        ).order_by(
            CIGIMessage.published_at.desc()
        ).limit(3).all()

        if latest_messages:
            logger.info("\n最新的3条记录:")
            for msg in latest_messages:
                logger.info(f"  - {msg.title[:50]}... ({msg.published_at})")
                logger.info(f"    URL: {msg.url}")
                logger.info(f"    类型: {msg.content_type}")
                logger.info(f"    作者: {msg.provider}")

    logger.info("=" * 60)
    logger.info(f"第 {round_num} 轮采集完成")
    logger.info("=" * 60)


async def main():
    """主函数"""
    logger.info("CIGI采集器测试脚本")
    logger.info("=" * 60)

    # 1. 加载配置
    config = ConfigManager()

    # 2. 初始化ChromaDB
    chroma_storage = initialize_chromadb(config)
    if not chroma_storage:
        logger.error("ChromaDB初始化失败，退出")
        return

    # 3. 初始化LLM客户端
    if not init_llm_clients(config):
        logger.error("LLM客户端初始化失败，退出")
        return

    # 4. 加载配置文件
    if not config.load_config():
        logger.error("配置文件加载失败，退出")
        return

    # 5. 查询消息源配置
    db_config = config.get_config().get('database', {})
    engine = create_engine(
        f"mysql+pymysql://{db_config['user']}:{db_config['password']}@"
        f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
        f"?charset=utf8mb4"
    )
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        source = session.query(MessageSource).filter(
            MessageSource.name == 'cigi_ai'
        ).first()

        if not source:
            logger.error("未找到cigi_ai消息源，请先执行register.sql注册")
            return

        logger.info(f"找到消息源: {source.display_name} (ID: {source.id})")

        # 5. 创建采集器实例
        collector_config = {
            'id': source.id,
            'mysql_table': source.config.get('mysql_table'),
            'chroma_collection': source.config.get('chroma_collection'),
            'interval': source.config.get('interval', 86400),
            'config': source.config
        }

        collector = CIGICollector(collector_config)

        if not await collector.initialize():
            logger.error("采集器初始化失败，退出")
            return

        # 6. 第一次测试采集
        await test_collector_once(collector, 1)

        # 7. 等待3秒
        logger.info("\n等待3秒后进行第二次采集...")
        await asyncio.sleep(3)

        # 8. 第二次测试采集（验证去重）
        await test_collector_once(collector, 2)

        # 9. 关闭浏览器
        await collector._close_browser()

        logger.info("\n" + "=" * 60)
        logger.info("测试完成！")
        logger.info("预期结果:")
        logger.info("  - 第1轮：应该采集到新文章")
        logger.info("  - 第2轮：应该0条新文章（去重生效）")
        logger.info("=" * 60)

    finally:
        session.close()


if __name__ == '__main__':
    # Windows环境需要设置事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())
