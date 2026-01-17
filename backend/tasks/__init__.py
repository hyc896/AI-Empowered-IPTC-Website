# -*- coding: utf-8 -*-

"""
Celery Application
Celery任务队列应用入口
"""

import asyncio
import logging
import os
import sys
from typing import Optional

# 禁用Playwright遥测（必须在导入playwright之前设置）
os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"
os.environ["PW_DISABLE_TS_STATS"] = "1"

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown

# 导入配置
from backend.config import ConfigManager

logger = logging.getLogger(__name__)

# ========================
# Celery App实例
# ========================
app = Celery('message_platform')

# 从celeryconfig.py加载配置
app.config_from_object('backend.celeryconfig')

# Windows环境需要设置事件循环策略
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


# ========================
# Worker进程级资源（每个worker独立初始化）
# ========================
_worker_config: Optional[dict] = None
_worker_browser_pool: Optional['BrowserPool'] = None
_worker_chromadb_storage: Optional['ChromaDBStorage'] = None
_worker_event_loop: Optional[asyncio.AbstractEventLoop] = None


def get_worker_browser_pool() -> Optional['BrowserPool']:
    """获取当前worker的浏览器池"""
    return _worker_browser_pool


def get_worker_chromadb() -> Optional['ChromaDBStorage']:
    """获取当前worker的ChromaDB存储"""
    return _worker_chromadb_storage


def get_worker_event_loop() -> asyncio.AbstractEventLoop:
    """获取当前worker的事件循环"""
    global _worker_event_loop
    if _worker_event_loop is None:
        _worker_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_event_loop)
    return _worker_event_loop


# ========================
# Worker启动钩子
# ========================
@worker_process_init.connect
def init_worker(**kwargs):
    """
    Worker进程启动时初始化资源

    每个worker进程独立初始化：
    - 事件循环
    - 配置管理器
    - 浏览器池（每个worker独立池，容量调整为max=3）
    - ChromaDB客户端（server模式，连接11530端口）
    """
    global _worker_config, _worker_browser_pool, _worker_chromadb_storage, _worker_event_loop

    try:
        logger.info("=" * 60)
        logger.info("【Worker启动】初始化worker进程资源...")

        # 1. 创建独立事件循环
        _worker_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_event_loop)
        logger.info("✓ 事件循环已创建")

        # 2. 加载配置
        config_manager = ConfigManager()
        if not config_manager.load_config('config.yaml'):
            raise RuntimeError("配置加载失败")
        _worker_config = config_manager.get_config()
        logger.info("✓ 配置加载成功")

        # 2.5. 注册ORM类（用于AI日报等功能）
        try:
            from backend.database.orm_registry import auto_register_all_models
            auto_register_all_models()
            logger.info("✓ ORM类注册成功")
        except Exception as e:
            logger.error(f"❌ ORM类注册失败: {e}")
            raise

        # 3. 初始化BrowserPool（worker级独立池）
        try:
            from backend.services.browser_pool import BrowserPool

            browser_config = _worker_config.get('browser_pool', {})
            # Worker级浏览器池容量调整（避免资源过度占用）
            browser_config['min_size'] = 0
            browser_config['max_size'] = 3  # 每个worker最多3个浏览器
            browser_config['init_size'] = 1  # 启动时创建1个

            _worker_browser_pool = BrowserPool(browser_config)

            # 在事件循环中初始化
            async def init_browser_pool():
                success = await _worker_browser_pool.initialize()
                if not success:
                    raise RuntimeError("BrowserPool初始化失败")
                logger.info("✓ BrowserPool初始化成功（容量: 0-3）")

            _worker_event_loop.run_until_complete(init_browser_pool())

        except ImportError:
            logger.warning("⚠ Playwright未安装，浏览器池不可用")
            _worker_browser_pool = None
        except Exception as e:
            logger.error(f"❌ BrowserPool初始化失败: {e}")
            _worker_browser_pool = None

        # 4. 初始化ChromaDB（server模式）
        try:
            from backend.storage import initialize_chromadb
            import os

            chroma_config = _worker_config.get('database', {}).get('chromadb', {})

            # 使用local模式（从环境变量CHROMADB_MODE读取，默认local）
            # Server模式在Windows上有兼容性问题，优先使用local模式
            chroma_mode = os.getenv('CHROMADB_MODE', 'local')
            chroma_config['mode'] = chroma_mode

            # 使用全局初始化函数，确保采集器能通过 get_chromadb_storage() 访问
            if initialize_chromadb(chroma_config):
                logger.info(f"✓ ChromaDB初始化成功（模式: {chroma_mode}）")
                # 同时保存到 Worker 本地变量（兼容性）
                from backend.storage import get_chromadb_storage
                _worker_chromadb_storage = get_chromadb_storage()
            else:
                logger.warning("⚠ ChromaDB初始化失败，向量化功能不可用")
                _worker_chromadb_storage = None

        except Exception as e:
            logger.error(f"❌ ChromaDB初始化失败: {e}")
            _worker_chromadb_storage = None

        # 5. 初始化GlobalLLMManager（Chat、Embedding、Fast）
        try:
            from backend.llm.global_llm_manager import GlobalLLMManager

            llm_config = _worker_config.get("llm", {})

            if llm_config:
                chat_config = llm_config.get("chat", {})
                embedding_config = llm_config.get("embedding", {})
                fast_config = llm_config.get("fast", {})

                llm_manager = GlobalLLMManager.get_instance()
                llm_manager.initialize(
                    chat_config=chat_config,
                    embedding_config=embedding_config,
                    fast_config=fast_config
                )

                logger.info("✓ GlobalLLMManager初始化成功")
                if chat_config:
                    logger.info(f"  Chat: {chat_config.get('model')}")
                if embedding_config:
                    logger.info(f"  Embedding: {embedding_config.get('model')}")
                if fast_config:
                    logger.info(f"  Fast: {fast_config.get('model')}")
            else:
                logger.warning("⚠ LLM配置为空，跳过初始化")

        except Exception as e:
            logger.error(f"❌ GlobalLLMManager初始化失败: {e}")
            logger.warning("⚠ Worker将在没有LLM功能的情况下运行")

        logger.info("【Worker启动】资源初始化完成")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"【Worker启动】资源初始化失败: {e}", exc_info=True)
        raise


# ========================
# Worker关闭钩子
# ========================
@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    """
    Worker进程关闭时清理资源

    清理顺序：
    1. 关闭BrowserPool
    2. 关闭ChromaDB（如需要）
    3. 关闭事件循环
    """
    global _worker_browser_pool, _worker_chromadb_storage, _worker_event_loop

    logger.info("=" * 60)
    logger.info("【Worker关闭】清理worker进程资源...")

    try:
        # 1. 清理BrowserPool
        if _worker_browser_pool:
            async def cleanup_browser_pool():
                await _worker_browser_pool.cleanup()
                logger.info("✓ BrowserPool已清理")

            if _worker_event_loop and not _worker_event_loop.is_closed():
                _worker_event_loop.run_until_complete(cleanup_browser_pool())
            _worker_browser_pool = None

        # 2. 清理ChromaDB（客户端模式无需显式关闭）
        if _worker_chromadb_storage:
            _worker_chromadb_storage = None
            logger.info("✓ ChromaDB已清理")

        # 3. 关闭事件循环
        if _worker_event_loop and not _worker_event_loop.is_closed():
            _worker_event_loop.close()
            logger.info("✓ 事件循环已关闭")
            _worker_event_loop = None

        logger.info("【Worker关闭】资源清理完成")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"【Worker关闭】资源清理失败: {e}", exc_info=True)


# ========================
# 辅助函数：在Worker事件循环中运行异步任务
# ========================
def run_async_task(coro):
    """
    在Worker的事件循环中运行异步任务

    【重要】必须使用Worker初始化时创建的事件循环，原因：
    - BrowserPool/Playwright在Worker启动时初始化，绑定到_worker_event_loop
    - Playwright的Browser对象只能在创建它的事件循环中使用
    - 如果创建新的事件循环，Playwright调用会死锁

    Args:
        coro: 协程对象

    Returns:
        异步任务的返回值
    """
    global _worker_event_loop

    # 使用Worker的事件循环
    if _worker_event_loop is None or _worker_event_loop.is_closed():
        # 如果Worker事件循环不可用，创建新的（降级方案）
        logger.warning("【run_async_task】Worker事件循环不可用，创建临时循环")
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            loop.close()
    else:
        # 使用Worker的事件循环（正常情况）
        asyncio.set_event_loop(_worker_event_loop)
        return _worker_event_loop.run_until_complete(coro)


__all__ = [
    'app',
    'get_worker_browser_pool',
    'get_worker_chromadb',
    'get_worker_event_loop',
    'run_async_task',
]
