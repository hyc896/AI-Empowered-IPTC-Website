# -*- coding: utf-8 -*-

"""
系统监控API路由
提供综合系统状态监控，替代Flower进行轻量级监控
"""

import json
import logging
import redis
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.tasks import app as celery_app
from backend.database.connection import create_session, check_database_connection
from backend.database.entities import MessageSource
from backend.config import ConfigManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/monitor",
    tags=["系统监控"]
)

# Redis键前缀（用于存储采集器统计）
COLLECTOR_STATS_KEY_PREFIX = "collector_stats:"
_app_start_time: Optional[datetime] = None
_redis_client: Optional[redis.Redis] = None


def _parse_celery_message(raw_message: str, queue_name: str) -> Optional[Dict[str, Any]]:
    """
    解析 Celery/Kombu 的 Redis 消息格式，提取任务详情

    Args:
        raw_message: Redis 中的原始 JSON 消息
        queue_name: 队列名称

    Returns:
        解析后的任务详情字典，解析失败返回 None
    """
    try:
        msg = json.loads(raw_message)

        # 从 headers 获取信息
        headers = msg.get('headers', {})
        properties = msg.get('properties', {})

        task_full_name = headers.get('task', 'unknown')
        task_name = task_full_name.split('.')[-1]
        task_id = headers.get('id', properties.get('correlation_id', 'unknown'))

        # 解析参数（从 argsrepr 或 body）
        args = []
        argsrepr = headers.get('argsrepr', '')
        if argsrepr:
            # 格式如 "('tonghuashun',)" 或 "('governance', None)"
            argsrepr = argsrepr.strip('()')
            if argsrepr:
                for part in argsrepr.split(','):
                    part = part.strip().strip("'\"")
                    if part and part != 'None':
                        args.append(part)

        # 获取时间限制
        timelimit = headers.get('timelimit', [None, None])
        time_limit = timelimit[0] if timelimit and len(timelimit) > 0 else None

        # 获取优先级
        priority = properties.get('priority', headers.get('priority', 5))

        return {
            'id': task_id[:8] if task_id and len(task_id) > 8 else task_id,
            'name': task_name,
            'full_name': task_full_name,
            'args': args,
            'priority': priority,
            'queue': queue_name,
            'eta': headers.get('eta'),
            'time_limit': time_limit
        }
    except Exception as e:
        logger.warning(f"解析任务消息失败: {e}")
        return None


def _get_queue_tasks(r: redis.Redis, queue_name: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    获取队列中的待执行任务列表

    Args:
        r: Redis 客户端
        queue_name: 队列名称
        limit: 最大返回数量

    Returns:
        任务详情列表
    """
    tasks = []
    try:
        messages = r.lrange(queue_name, 0, limit - 1)
        for raw_msg in messages:
            task = _parse_celery_message(raw_msg, queue_name)
            if task:
                tasks.append(task)
    except Exception as e:
        logger.warning(f"获取队列 {queue_name} 任务失败: {e}")
    return tasks


def _get_redis_client() -> Optional[redis.Redis]:
    """获取Redis客户端（用于统计数据存储）"""
    global _redis_client
    if _redis_client is None:
        try:
            config_manager = ConfigManager()
            config_manager.load_config('config.yaml')
            config = config_manager.get_config()
            celery_config = config.get('celery', {})
            broker_url = celery_config.get('broker', {}).get('url', 'redis://localhost:6379/0')
            _redis_client = redis.from_url(broker_url, socket_connect_timeout=2, decode_responses=True)
            _redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis连接失败，统计数据将无法持久化: {e}")
            _redis_client = None
    return _redis_client


def _get_collector_stats(source_name: str) -> Dict[str, Any]:
    """从Redis获取采集器统计"""
    default_stats = {
        "total_runs": 0,
        "success_count": 0,
        "failure_count": 0,
        "last_run_at": None,
        "last_error": None
    }

    r = _get_redis_client()
    if not r:
        return default_stats

    try:
        data = r.get(f"{COLLECTOR_STATS_KEY_PREFIX}{source_name}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning(f"读取采集器统计失败: {source_name}, {e}")

    return default_stats


def _set_collector_stats(source_name: str, stats: Dict[str, Any]) -> None:
    """保存采集器统计到Redis"""
    r = _get_redis_client()
    if not r:
        return

    try:
        r.set(f"{COLLECTOR_STATS_KEY_PREFIX}{source_name}", json.dumps(stats, default=str))
    except Exception as e:
        logger.warning(f"保存采集器统计失败: {source_name}, {e}")


def _init_app_start_time():
    """初始化应用启动时间"""
    global _app_start_time
    if _app_start_time is None:
        _app_start_time = datetime.now()


def _get_time_ago(dt: Optional[datetime]) -> str:
    """将时间转换为"多久前"的格式"""
    if not dt:
        return "从未"

    now = datetime.now()
    diff = now - dt

    if diff.total_seconds() < 60:
        return f"{int(diff.total_seconds())}秒前"
    elif diff.total_seconds() < 3600:
        return f"{int(diff.total_seconds() / 60)}分钟前"
    elif diff.total_seconds() < 86400:
        return f"{int(diff.total_seconds() / 3600)}小时前"
    else:
        return f"{int(diff.total_seconds() / 86400)}天前"


def _check_redis_connection(config: dict) -> Dict[str, Any]:
    """检查Redis连接状态"""
    result = {
        "status": "unknown",
        "broker_connected": False,
        "backend_connected": False,
        "error": None
    }

    try:
        celery_config = config.get('celery', {})
        broker_url = celery_config.get('broker', {}).get('url', 'redis://localhost:6379/1')
        backend_url = celery_config.get('result_backend', {}).get('url', 'redis://localhost:6379/2')

        # 检查Broker连接
        try:
            r_broker = redis.from_url(broker_url, socket_connect_timeout=2)
            r_broker.ping()
            result["broker_connected"] = True
        except Exception as e:
            result["error"] = f"Broker连接失败: {str(e)}"

        # 检查Result Backend连接
        try:
            r_backend = redis.from_url(backend_url, socket_connect_timeout=2)
            r_backend.ping()
            result["backend_connected"] = True
        except Exception as e:
            if result["error"]:
                result["error"] += f"; Backend连接失败: {str(e)}"
            else:
                result["error"] = f"Backend连接失败: {str(e)}"

        # 整体状态判断
        if result["broker_connected"] and result["backend_connected"]:
            result["status"] = "healthy"
        elif result["broker_connected"] or result["backend_connected"]:
            result["status"] = "degraded"
        else:
            result["status"] = "unhealthy"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def _check_celery_worker() -> Dict[str, Any]:
    """
    检查Celery Worker状态

    注意：Windows环境使用Solo Pool模式，Worker执行任务时无法响应inspect请求。
    因此采用多重检测策略：
    1. 优先检测inspect ping（空闲时准确）
    2. 如果ping失败，检查Redis中是否有最近执行记录（间接证明Worker在工作）
    3. 检查队列中的任务是否被消费（队列长度是否在减少）
    """
    result = {
        "status": "unknown",
        "count": 0,
        "workers": [],
        "active_tasks": 0,
        "busy": False,  # 新增：标记Worker是否正忙于执行任务
        "error": None
    }

    try:
        # 方式1：尝试inspect ping（Worker空闲时有效）
        inspect = celery_app.control.inspect(timeout=2)  # 缩短超时，快速失败
        ping_result = inspect.ping()

        if ping_result:
            # Worker空闲，能响应ping
            result["workers"] = list(ping_result.keys())
            result["count"] = len(ping_result)
            result["status"] = "healthy"

            # 获取活跃任务数
            try:
                active = inspect.active()
                if active:
                    for worker_tasks in active.values():
                        result["active_tasks"] += len(worker_tasks) if worker_tasks else 0
            except Exception:
                pass
            return result

        # 方式2：ping失败，检查是否因为Worker正忙
        # 通过检查Redis中的采集器统计判断Worker是否在工作
        r = _get_redis_client()
        if r:
            try:
                # 检查最近5分钟内是否有任务执行记录
                now = datetime.now()
                recent_activity = False

                keys = r.keys(f"{COLLECTOR_STATS_KEY_PREFIX}*")
                for key in keys[:10]:  # 检查前10个
                    data = r.get(key)
                    if data:
                        stats = json.loads(data)
                        last_run = stats.get("last_run_at")
                        if last_run:
                            try:
                                last_run_dt = datetime.fromisoformat(last_run.replace('Z', '+00:00').replace('+00:00', ''))
                                if (now - last_run_dt).total_seconds() < 300:  # 5分钟内
                                    recent_activity = True
                                    break
                            except (ValueError, TypeError):
                                pass

                if recent_activity:
                    # 有最近活动，说明Worker在工作但忙碌
                    result["status"] = "healthy"
                    result["count"] = 1  # 至少1个Worker
                    result["busy"] = True
                    result["error"] = None
                    return result

            except Exception as e:
                logger.warning(f"检测Worker状态时Redis操作失败: {e}")

        # 方式3：检查数据库中最近的采集记录（最可靠的间接证据）
        # 即使Redis统计为空，数据库的last_crawled_at也能证明Worker在工作
        try:
            now = datetime.now()
            with create_session() as db:
                recent_source = db.query(MessageSource).filter(
                    MessageSource.last_crawled_at >= now - timedelta(minutes=10)
                ).first()
                if recent_source:
                    result["status"] = "healthy"
                    result["count"] = 1
                    result["busy"] = True
                    result["error"] = None
                    return result
        except Exception as e:
            logger.warning(f"检测Worker状态时数据库查询失败: {e}")

        # 所有检测都失败
        result["status"] = "unhealthy"
        result["error"] = "没有活跃的Worker（或Worker正忙于长任务）"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def _check_celery_beat() -> Dict[str, Any]:
    """
    检查Celery Beat状态

    注意：Beat进程不通过inspect检测，而是检查Redis中的心跳或任务调度记录。
    由于Beat是独立进程，无法通过Worker inspect获取其状态。
    改用更可靠的方式：检查是否有定时任务被注册。
    """
    result = {
        "status": "unknown",
        "scheduled_tasks": 0,
        "registered_tasks": 0,
        "error": None
    }

    try:
        # 从Beat Schedule获取注册的定时任务数
        from backend.tasks.beat_schedule import beat_schedule
        result["registered_tasks"] = len(beat_schedule)

        if result["registered_tasks"] > 0:
            # 有注册的定时任务，假设Beat配置正确
            # 注意：这只能确认配置存在，无法确认Beat进程是否运行
            # 真正确认需要检查Redis中的心跳或最近任务执行记录
            result["status"] = "healthy"
        else:
            result["status"] = "unknown"
            result["error"] = "没有注册的定时任务"

        # 尝试通过检查最近是否有任务被调度来判断Beat是否运行
        r = _get_redis_client()
        if r:
            try:
                # 检查是否有最近的采集任务执行（间接证明Beat在工作）
                keys = r.keys(f"{COLLECTOR_STATS_KEY_PREFIX}*")
                if keys:
                    # 有统计数据说明有任务执行过
                    recent_runs = 0
                    for key in keys[:5]:  # 只检查前5个
                        data = r.get(key)
                        if data:
                            stats = json.loads(data)
                            if stats.get("total_runs", 0) > 0:
                                recent_runs += 1
                    if recent_runs > 0:
                        result["status"] = "healthy"
                        result["scheduled_tasks"] = recent_runs
            except Exception:
                pass

    except ImportError:
        result["status"] = "unknown"
        result["error"] = "无法加载beat_schedule配置"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def _check_database() -> Dict[str, Any]:
    """检查数据库连接状态"""
    result = {
        "status": "unknown",
        "response_ms": 0,
        "error": None
    }

    try:
        start = datetime.now()
        is_connected = check_database_connection()
        elapsed = (datetime.now() - start).total_seconds() * 1000

        result["response_ms"] = round(elapsed, 2)

        if is_connected:
            result["status"] = "healthy"
        else:
            result["status"] = "unhealthy"
            result["error"] = "数据库连接失败"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def _check_chromadb(config: dict) -> Dict[str, Any]:
    """检查ChromaDB状态"""
    result = {
        "status": "unknown",
        "collections": 0,
        "mode": "unknown",
        "error": None
    }

    try:
        from backend.storage import get_chromadb_storage

        storage = get_chromadb_storage()
        if not storage or not storage.is_initialized():
            result["status"] = "unhealthy"
            result["error"] = "ChromaDB未初始化"
            return result

        chromadb_config = config.get('database', {}).get('chromadb', {})
        result["mode"] = chromadb_config.get('mode', 'local')

        # 获取集合数量
        if hasattr(storage, '_client') and storage._client:
            collections = storage._client.list_collections()
            result["collections"] = len(collections)

        result["status"] = "healthy"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def _get_collector_stats_from_db() -> List[Dict[str, Any]]:
    """从数据库获取采集器统计信息"""
    collectors = []

    try:
        with create_session() as db:
            sources = db.query(MessageSource).filter(
                MessageSource.is_active == True
            ).all()

            for source in sources:
                config = source.config or {}
                interval = config.get('interval', 300)

                # 计算下次运行时间
                next_run_in = None
                if source.last_crawled_at:
                    next_run_at = source.last_crawled_at + timedelta(seconds=interval)
                    remaining = (next_run_at - datetime.now()).total_seconds()
                    if remaining > 0:
                        if remaining < 60:
                            next_run_in = f"{int(remaining)}秒后"
                        else:
                            next_run_in = f"{int(remaining / 60)}分钟后"
                    else:
                        next_run_in = "即将运行"

                # 从Redis获取运行次数统计
                stats = _get_collector_stats(source.name)

                collectors.append({
                    "name": source.name,
                    "display_name": source.display_name or source.name,
                    "category": source.category,
                    "status": "healthy",  # 默认健康，后续可根据失败率判断
                    "interval": interval,
                    "total_runs": stats.get("total_runs", 0),
                    "success_count": stats.get("success_count", 0),
                    "failure_count": stats.get("failure_count", 0),
                    "last_run_at": source.last_crawled_at.isoformat() if source.last_crawled_at else None,
                    "last_run_ago": _get_time_ago(source.last_crawled_at),
                    "next_run_in": next_run_in,
                    "last_error": stats.get("last_error")
                })

                # 根据失败率判断状态
                if stats.get("failure_count", 0) > 0:
                    total = stats.get("total_runs", 0)
                    if total > 0:
                        failure_rate = stats.get("failure_count", 0) / total
                        if failure_rate > 0.5:
                            collectors[-1]["status"] = "unhealthy"
                        elif failure_rate > 0.2:
                            collectors[-1]["status"] = "degraded"

    except Exception as e:
        logger.error(f"获取采集器统计失败: {e}")

    return collectors


@router.get("/system")
async def get_system_monitor() -> Dict[str, Any]:
    """
    获取综合系统监控状态

    返回Redis、Celery Worker、Celery Beat、数据库、ChromaDB的状态，
    以及所有采集器的运行统计
    """
    _init_app_start_time()

    # 加载配置
    config_manager = ConfigManager()
    config_manager.load_config('config.yaml')
    config = config_manager.get_config()

    # 并行检查各组件状态
    redis_status = _check_redis_connection(config)
    worker_status = _check_celery_worker()
    beat_status = _check_celery_beat()
    database_status = _check_database()
    chromadb_status = _check_chromadb(config)
    collectors = _get_collector_stats_from_db()

    # 计算整体状态
    component_statuses = [
        redis_status["status"],
        worker_status["status"],
        database_status["status"],
        chromadb_status["status"]
    ]

    if all(s == "healthy" for s in component_statuses):
        overall_status = "healthy"
    elif any(s in ["unhealthy", "error"] for s in component_statuses):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    # 计算运行时长
    uptime = None
    if _app_start_time:
        uptime_seconds = (datetime.now() - _app_start_time).total_seconds()
        if uptime_seconds < 3600:
            uptime = f"{int(uptime_seconds / 60)}分钟"
        elif uptime_seconds < 86400:
            uptime = f"{int(uptime_seconds / 3600)}小时"
        else:
            uptime = f"{int(uptime_seconds / 86400)}天"

    return {
        "overall_status": overall_status,
        "uptime": uptime,
        "timestamp": datetime.now().isoformat(),
        "components": {
            "redis": redis_status,
            "celery_worker": worker_status,
            "celery_beat": beat_status,
            "database": database_status,
            "chromadb": chromadb_status
        },
        "collectors": collectors,
        "summary": {
            "total_collectors": len(collectors),
            "healthy_collectors": sum(1 for c in collectors if c["status"] == "healthy"),
            "total_runs": sum(c.get("total_runs", 0) for c in collectors),
            "total_success": sum(c.get("success_count", 0) for c in collectors),
            "total_failures": sum(c.get("failure_count", 0) for c in collectors)
        }
    }


@router.post("/collector/{source_name}/record")
async def record_collector_execution(
    source_name: str,
    success: bool,
    error: Optional[str] = None
) -> Dict[str, Any]:
    """
    记录采集器执行结果（由Celery任务回调）

    Args:
        source_name: 消息源名称
        success: 是否成功
        error: 错误信息（如果失败）
    """
    # 从Redis读取当前统计
    stats = _get_collector_stats(source_name)

    stats["total_runs"] += 1
    stats["last_run_at"] = datetime.now().isoformat()

    if success:
        stats["success_count"] += 1
        stats["last_error"] = None
    else:
        stats["failure_count"] += 1
        stats["last_error"] = error

    # 保存回Redis
    _set_collector_stats(source_name, stats)

    return {"success": True, "stats": stats}


@router.get("/collectors/detail")
async def get_collectors_detail() -> List[Dict[str, Any]]:
    """
    获取所有采集器的详细状态
    """
    return _get_collector_stats_from_db()


@router.get("/redis")
async def get_redis_status() -> Dict[str, Any]:
    """
    获取Redis详细状态
    """
    config_manager = ConfigManager()
    config_manager.load_config('config.yaml')
    config = config_manager.get_config()

    result = _check_redis_connection(config)

    # 获取更多Redis信息
    try:
        celery_config = config.get('celery', {})
        broker_url = celery_config.get('broker', {}).get('url', 'redis://localhost:6379/1')

        r = redis.from_url(broker_url, socket_connect_timeout=2)
        info = r.info()

        result["details"] = {
            "redis_version": info.get("redis_version"),
            "connected_clients": info.get("connected_clients"),
            "used_memory_human": info.get("used_memory_human"),
            "uptime_in_seconds": info.get("uptime_in_seconds")
        }
    except Exception as e:
        result["details"] = {"error": str(e)}

    return result


@router.get("/workers")
async def get_workers_status() -> Dict[str, Any]:
    """
    获取Celery Worker详细状态
    """
    result = _check_celery_worker()

    # 获取更多Worker信息
    try:
        inspect = celery_app.control.inspect(timeout=2)
        stats = inspect.stats()
        active = inspect.active()
        reserved = inspect.reserved()
        registered = inspect.registered()

        if stats:
            result["worker_details"] = {}
            for worker_name, worker_stats in stats.items():
                result["worker_details"][worker_name] = {
                    "pool": worker_stats.get("pool", {}).get("implementation"),
                    "concurrency": worker_stats.get("pool", {}).get("max-concurrency"),
                    "active_tasks": len(active.get(worker_name, [])) if active else 0,
                    "reserved_tasks": len(reserved.get(worker_name, [])) if reserved else 0,
                    "registered_tasks": len(registered.get(worker_name, [])) if registered else 0
                }
    except Exception as e:
        result["worker_details"] = {"error": str(e)}

    return result


@router.get("/queues")
async def get_queue_status(
    include_tasks: bool = True,
    task_limit: int = 20
) -> Dict[str, Any]:
    """
    获取Celery队列状态（包含待执行、执行中、最近完成的任务）

    Args:
        include_tasks: 是否包含待执行任务的详情列表
        task_limit: 每个队列最大返回的任务数量（1-50）
    """
    task_limit = max(1, min(50, task_limit))

    result = {
        "queues": {},
        "active_tasks": [],
        "recent_tasks": [],
        "error": None
    }

    try:
        config_manager = ConfigManager()
        config_manager.load_config('config.yaml')
        config = config_manager.get_config()

        celery_config = config.get('celery', {})
        broker_url = celery_config.get('broker', {}).get('url', 'redis://localhost:6379/1')

        r = redis.from_url(broker_url, socket_connect_timeout=2, decode_responses=True)

        # 1. 检查待执行任务队列（与Worker监听的队列一致）
        for queue_name in ['default', 'collector', 'report']:
            try:
                length = r.llen(queue_name)
                queue_info = {"pending_tasks": length, "tasks": []}

                if include_tasks and length > 0:
                    queue_info["tasks"] = _get_queue_tasks(r, queue_name, task_limit)

                result["queues"][queue_name] = queue_info
            except Exception:
                result["queues"][queue_name] = {"pending_tasks": 0, "tasks": []}

        # 2. 获取正在执行的任务（通过Celery inspect）
        try:
            inspect = celery_app.control.inspect(timeout=2)
            active = inspect.active()
            if active:
                for worker_name, tasks in active.items():
                    for task in (tasks or []):
                        result["active_tasks"].append({
                            "id": task.get("id"),
                            "name": task.get("name", "").split(".")[-1],
                            "args": task.get("args", []),
                            "worker": worker_name.split("@")[-1],
                            "started_at": task.get("time_start"),
                            "status": "running"
                        })
        except Exception as e:
            logger.debug(f"获取活跃任务失败（Worker可能忙碌）: {e}")

        # 3. 获取最近完成的任务（从Redis统计中提取）
        try:
            keys = r.keys(f"{COLLECTOR_STATS_KEY_PREFIX}*")
            recent_list = []
            for key in keys:
                data = r.get(key)
                if data:
                    stats = json.loads(data)
                    last_run = stats.get("last_run_at")
                    if last_run:
                        source_name = key.replace(COLLECTOR_STATS_KEY_PREFIX, "")
                        recent_list.append({
                            "name": f"run_collector",
                            "source": source_name,
                            "completed_at": last_run,
                            "success": stats.get("last_error") is None,
                            "error": stats.get("last_error"),
                            "status": "success" if stats.get("last_error") is None else "failed"
                        })

            # 按完成时间排序，取最近10条
            recent_list.sort(key=lambda x: x["completed_at"] or "", reverse=True)
            result["recent_tasks"] = recent_list[:10]

        except Exception as e:
            logger.debug(f"获取最近任务失败: {e}")

    except Exception as e:
        result["error"] = str(e)

    return result


@router.delete("/queues/{queue_name}")
async def clear_queue(queue_name: str) -> Dict[str, Any]:
    """
    清空指定队列中的所有待执行任务

    Args:
        queue_name: 队列名称（default/collector/report）

    Returns:
        清空结果，包含删除的任务数量
    """
    allowed_queues = ['default', 'collector', 'report']
    if queue_name not in allowed_queues:
        raise HTTPException(status_code=400, detail=f"无效的队列名称，允许值: {allowed_queues}")

    try:
        config_manager = ConfigManager()
        config_manager.load_config('config.yaml')
        config = config_manager.get_config()

        celery_config = config.get('celery', {})
        broker_url = celery_config.get('broker', {}).get('url', 'redis://localhost:6379/1')

        r = redis.from_url(broker_url, socket_connect_timeout=2, decode_responses=True)

        # 获取队列长度
        length = r.llen(queue_name)

        # 清空队列
        if length > 0:
            r.delete(queue_name)
            logger.info(f"已清空队列 {queue_name}，删除 {length} 个任务")

        return {
            "queue": queue_name,
            "cleared_tasks": length
        }

    except Exception as e:
        logger.error(f"清空队列 {queue_name} 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
