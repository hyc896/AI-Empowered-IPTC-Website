# -*- coding: utf-8 -*-

"""
Collector Celery Tasks
采集器Celery任务定义
"""

import logging
import importlib
from typing import Dict, Any, Optional
from datetime import datetime

from backend.tasks import app, get_worker_browser_pool, run_async_task
from backend.database.connection import create_session
from backend.database.entities import MessageSource

logger = logging.getLogger(__name__)


@app.task(
    name='backend.tasks.collector_tasks.run_collector',
    bind=True,
    max_retries=2,
    default_retry_delay=300,  # 失败后5分钟重试
    time_limit=600,  # 10分钟硬限制
    soft_time_limit=540  # 9分钟软限制
)
def run_collector(self, source_name: str) -> Dict[str, Any]:
    """
    运行指定采集器（单次采集）

    Args:
        source_name: 消息源名称（如 tonghuashun, kr36）

    Returns:
        采集结果字典: {
            'success': bool,
            'source_name': str,
            'collected_count': int,
            'duration_seconds': float,
            'error': str | None
        }

    Raises:
        Retry: 采集失败时自动重试
    """
    start_time = datetime.now()
    logger.info(f"【Celery采集器】开始采集: {source_name}")

    try:
        # 1. 从数据库加载消息源配置
        source_config = _load_source_config(source_name)
        if not source_config:
            error_msg = f"消息源 '{source_name}' 不存在或未激活"
            logger.error(f"【Celery采集器】{error_msg}")
            return {
                'success': False,
                'source_name': source_name,
                'collected_count': 0,
                'duration_seconds': 0,
                'error': error_msg
            }

        # 2. 动态导入采集器模块
        collector_module_path = source_config.get('collector_module')
        if not collector_module_path:
            error_msg = f"消息源 '{source_name}' 未配置 collector_module"
            logger.error(f"【Celery采集器】{error_msg}")
            return {
                'success': False,
                'source_name': source_name,
                'collected_count': 0,
                'duration_seconds': 0,
                'error': error_msg
            }

        # 3. 创建采集器实例
        collector_instance = _create_collector_instance(collector_module_path, source_config)
        if not collector_instance:
            error_msg = f"创建采集器实例失败: {source_name}"
            logger.error(f"【Celery采集器】{error_msg}")
            return {
                'success': False,
                'source_name': source_name,
                'collected_count': 0,
                'duration_seconds': 0,
                'error': error_msg
            }

        # 4. 注入浏览器池（如果采集器需要）
        browser_pool = get_worker_browser_pool()
        if hasattr(collector_instance, 'set_browser_pool') and browser_pool:
            collector_instance.set_browser_pool(browser_pool)
            logger.debug(f"【Celery采集器】已注入浏览器池: {source_name}")

        # 5. 初始化采集器（如果需要）
        if hasattr(collector_instance, 'initialize'):
            async def init_collector():
                success = await collector_instance.initialize()
                if not success:
                    raise RuntimeError(f"采集器初始化失败: {source_name}")

            run_async_task(init_collector())
            logger.info(f"【Celery采集器】初始化成功: {source_name}")

        # 6. 执行单次采集
        async def collect_once():
            if hasattr(collector_instance, 'collect_once'):
                # PlaywrightCollectorBase及其子类使用 collect_once()
                result = await collector_instance.collect_once()
            elif hasattr(collector_instance, 'collect'):
                # 旧版采集器使用 collect()
                result = await collector_instance.collect()
            elif hasattr(collector_instance, '_collect_once'):
                # RSS采集器使用 _collect_once()（私有方法）
                await collector_instance._collect_once()
                # RSS采集器通常不返回结果字典，构造标准格式
                result = {'collected': 1, 'success': True, 'error': None}
            else:
                raise AttributeError(f"采集器 {source_name} 缺少 collect_once()、collect() 或 _collect_once() 方法")

            return result

        result = run_async_task(collect_once())

        # 7. 更新last_crawled_at时间戳
        _update_last_crawled_at(source_name)

        # 8. 返回结果
        duration_seconds = (datetime.now() - start_time).total_seconds()
        collected_count = result.get('collected', 0) if isinstance(result, dict) else 0

        logger.info(
            f"【Celery采集器】✓ 采集成功: {source_name} "
            f"(采集: {collected_count}, 耗时: {duration_seconds:.2f}s)"
        )

        return {
            'success': True,
            'source_name': source_name,
            'collected_count': collected_count,
            'duration_seconds': duration_seconds,
            'error': None
        }

    except Exception as e:
        duration_seconds = (datetime.now() - start_time).total_seconds()
        logger.error(f"【Celery采集器】❌ 采集失败: {source_name}, 错误: {e}", exc_info=True)

        # 重试逻辑
        if self.request.retries < self.max_retries:
            logger.warning(f"【Celery采集器】重试中: {source_name} ({self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e)

        return {
            'success': False,
            'source_name': source_name,
            'collected_count': 0,
            'duration_seconds': duration_seconds,
            'error': str(e)
        }


# ========================
# 辅助函数
# ========================

def _load_source_config(source_name: str) -> Optional[Dict[str, Any]]:
    """
    从数据库加载消息源配置

    Args:
        source_name: 消息源名称

    Returns:
        消息源配置字典，如果不存在则返回None
    """
    try:
        with create_session() as db:
            source = db.query(MessageSource).filter(
                MessageSource.name == source_name,
                MessageSource.is_active == True
            ).first()

            if not source:
                return None

            config = source.config or {}

            return {
                "id": source.id,
                "name": source.name,
                "adapter_name": source.adapter_name,
                "category": source.category or config.get("source_type", "unknown"),
                "display_name": source.display_name or source.name,
                "mysql_table": config.get("mysql_table", f"{source.name}_messages"),
                "chroma_collection": config.get("chroma_collection", f"{source.name}_messages"),
                "collector_module": config.get("collector_module", ""),
                "interval": config.get("interval", 60),
                "enabled": True,
                "config": config,
                "last_crawled_at": source.last_crawled_at,
                "schedule": source.schedule
            }

    except Exception as e:
        logger.error(f"加载消息源配置失败: {source_name}, 错误: {e}")
        return None


def _create_collector_instance(module_path: str, source_config: Dict[str, Any]) -> Optional[Any]:
    """
    动态创建采集器实例

    Args:
        module_path: 模块路径（如 backend.sources.tonghuashun.collector）
        source_config: 消息源配置

    Returns:
        采集器实例，失败返回None
    """
    try:
        # 动态导入模块
        adjusted_module_path = module_path.replace("backend.services.message", "backend")
        module = importlib.import_module(adjusted_module_path)

        # 查找Collector类
        collector_class_name = None
        for attr_name in dir(module):
            if attr_name.endswith('Collector') and not attr_name.startswith('_'):
                collector_class_name = attr_name
                break

        if not collector_class_name:
            logger.error(f"模块 {module_path} 中未找到 Collector 类")
            return None

        # 创建实例
        collector_class = getattr(module, collector_class_name)
        return collector_class(source_config)

    except Exception as e:
        logger.error(f"创建采集器实例失败: {module_path}, 错误: {e}")
        return None


def _update_last_crawled_at(source_name: str) -> None:
    """
    更新消息源的最后采集时间

    Args:
        source_name: 消息源名称
    """
    try:
        with create_session() as db:
            source = db.query(MessageSource).filter(
                MessageSource.name == source_name
            ).first()

            if source:
                source.last_crawled_at = datetime.now()
                db.commit()

    except Exception as e:
        logger.error(f"更新last_crawled_at失败: {source_name}, 错误: {e}")
