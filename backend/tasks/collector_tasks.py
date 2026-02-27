# -*- coding: utf-8 -*-

"""
Collector Celery Tasks
采集器Celery任务定义
"""

import json
import logging
import importlib
import redis
from typing import Dict, Any, Optional
from datetime import datetime

from backend.tasks import app, get_worker_browser_pool, run_async_task
from backend.database.connection import create_session
from backend.database.entities import MessageSource
from backend.config import ConfigManager

logger = logging.getLogger(__name__)

# Redis统计键前缀（与monitor_routes保持一致）
COLLECTOR_STATS_KEY_PREFIX = "collector_stats:"
_redis_client: Optional[redis.Redis] = None


def _get_stats_redis_client() -> Optional[redis.Redis]:
    """获取Redis客户端用于统计记录"""
    global _redis_client
    if _redis_client is None:
        try:
            config_manager = ConfigManager()
            config_manager.load_config('config.yaml')
            config = config_manager.get_config()
            celery_config = config.get('celery', {})
            broker_url = celery_config.get('broker', {}).get('url', 'redis://localhost:6379/1')
            _redis_client = redis.from_url(broker_url, socket_connect_timeout=2, decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis连接失败，统计数据将不记录: {e}")
    return _redis_client


def _record_collector_stats(source_name: str, success: bool, error: Optional[str] = None) -> None:
    """记录采集器执行统计到Redis"""
    r = _get_stats_redis_client()
    if not r:
        return

    try:
        key = f"{COLLECTOR_STATS_KEY_PREFIX}{source_name}"
        data = r.get(key)
        if data:
            stats = json.loads(data)
        else:
            stats = {
                "total_runs": 0,
                "success_count": 0,
                "failure_count": 0,
                "last_run_at": None,
                "last_error": None
            }

        stats["total_runs"] += 1
        stats["last_run_at"] = datetime.now().isoformat()

        if success:
            stats["success_count"] += 1
            stats["last_error"] = None
        else:
            stats["failure_count"] += 1
            stats["last_error"] = error

        r.set(key, json.dumps(stats))
        logger.debug(f"【Celery采集器】统计已记录: {source_name}, 成功={success}")
    except Exception as e:
        logger.warning(f"记录采集器统计失败: {source_name}, {e}")


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

        try:
            result = run_async_task(collect_once())
        finally:
            # 【关键】采集完成后必须释放浏览器回池，否则浏览器池会耗尽
            if hasattr(collector_instance, '_close_browser'):
                async def release_browser():
                    await collector_instance._close_browser()
                try:
                    run_async_task(release_browser())
                    logger.debug(f"【Celery采集器】已释放浏览器: {source_name}")
                except Exception as release_err:
                    logger.warning(f"【Celery采集器】释放浏览器失败: {source_name}, {release_err}")

        # 7. 更新last_crawled_at时间戳
        _update_last_crawled_at(source_name)

        # 8. 返回结果
        duration_seconds = (datetime.now() - start_time).total_seconds()
        collected_count = result.get('collected', 0) if isinstance(result, dict) else 0

        logger.info(
            f"【Celery采集器】✓ 采集成功: {source_name} "
            f"(采集: {collected_count}, 耗时: {duration_seconds:.2f}s)"
        )

        # 9. 记录统计到Redis
        _record_collector_stats(source_name, success=True)

        return {
            'success': True,
            'source_name': source_name,
            'collected_count': collected_count,
            'duration_seconds': duration_seconds,
            'error': None
        }

    except Exception as e:
        # 【关键】异常时也必须释放浏览器，防止浏览器池泄漏
        if 'collector_instance' in locals() and hasattr(collector_instance, '_close_browser'):
            async def release_browser_on_error():
                await collector_instance._close_browser()
            try:
                run_async_task(release_browser_on_error())
                logger.debug(f"【Celery采集器】异常后已释放浏览器: {source_name}")
            except Exception as release_err:
                logger.warning(f"【Celery采集器】异常后释放浏览器失败: {source_name}, {release_err}")

        duration_seconds = (datetime.now() - start_time).total_seconds()
        logger.error(f"【Celery采集器】❌ 采集失败: {source_name}, 错误: {e}", exc_info=True)

        # 重试逻辑
        if self.request.retries < self.max_retries:
            logger.warning(f"【Celery采集器】重试中: {source_name} ({self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e)

        # 所有重试失败，记录失败统计
        _record_collector_stats(source_name, success=False, error=str(e))

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
                "config": config.get("config", {}),  # 传递嵌套的config对象，而不是整个source.config
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


@app.task(
    name='backend.tasks.collector_tasks.trigger_all_collectors',
    bind=True,
    time_limit=60,
    soft_time_limit=50
)
def trigger_all_collectors(self) -> Dict[str, Any]:
    """
    触发所有激活的采集器进入队列（用于启动时初始化）

    所有任务直接加入队列排队，由Worker串行消费

    Returns:
        触发结果字典
    """
    logger.info("【启动触发】开始触发所有采集器进入队列...")

    triggered = []
    failed = []

    try:
        with create_session() as db:
            active_sources = db.query(MessageSource).filter(
                MessageSource.is_active == True
            ).all()

            logger.info(f"【启动触发】发现 {len(active_sources)} 个激活的消息源")

            for source in active_sources:
                try:
                    run_collector.apply_async(
                        args=(source.name,),
                        queue='collector'
                    )

                    triggered.append({
                        'name': source.name,
                        'display_name': source.display_name or source.name
                    })

                    logger.info(f"【启动触发】已加入队列: {source.display_name or source.name}")

                except Exception as e:
                    failed.append({
                        'name': source.name,
                        'error': str(e)
                    })
                    logger.error(f"【启动触发】加入队列失败: {source.name}, 错误: {e}")

    except Exception as e:
        logger.error(f"【启动触发】获取消息源列表失败: {e}")
        return {
            'success': False,
            'triggered_count': 0,
            'failed_count': 0,
            'error': str(e)
        }

    logger.info(
        f"【启动触发】全部加入队列: 成功 {len(triggered)} 个, 失败 {len(failed)} 个"
    )

    return {
        'success': True,
        'triggered_count': len(triggered),
        'failed_count': len(failed),
        'triggered': triggered,
        'failed': failed
    }
