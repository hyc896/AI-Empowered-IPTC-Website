# -*- coding: utf-8 -*-

"""
采集器控制API路由（Celery版本）
提供采集器的触发、状态查询等功能
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

# 导入Celery任务
from backend.tasks.collector_tasks import run_collector
from backend.tasks import app as celery_app

from ..database.connection import create_session
from ..database.entities import MessageSource
from ..api.schemas import CollectorActionResponse

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/collectors",
    tags=["采集器管理"]
)


@router.get("/list")
async def get_collector_list() -> List[Dict[str, Any]]:
    """
    获取采集器列表

    返回所有激活的消息源采集器信息
    """
    try:
        with create_session() as db:
            sources = db.query(MessageSource).filter(
                MessageSource.is_active == True
            ).all()

            collector_list = []
            for source in sources:
                config = source.config or {}
                collector_list.append({
                    "name": source.name,
                    "display_name": source.display_name or source.name,
                    "category": source.category,
                    "interval": config.get("interval", 300),
                    "last_crawled_at": source.last_crawled_at.isoformat() if source.last_crawled_at else None
                })

            return collector_list

    except Exception as e:
        logger.error(f"获取采集器列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取采集器列表失败: {str(e)}"
        )


@router.post("/{source_name}/trigger", response_model=CollectorActionResponse)
async def trigger_manual_collect(source_name: str) -> CollectorActionResponse:
    """
    手动触发采集（异步）

    立即将采集任务提交到Celery队列，返回task_id

    Args:
        source_name: 消息源名称

    Returns:
        {
            "success": True,
            "message": "采集任务已提交",
            "task_id": "celery-task-id"
        }
    """
    try:
        # 1. 验证消息源是否存在且激活
        with create_session() as db:
            source = db.query(MessageSource).filter(
                MessageSource.name == source_name,
                MessageSource.is_active == True
            ).first()

            if not source:
                raise HTTPException(
                    status_code=404,
                    detail=f"消息源 '{source_name}' 不存在或未激活"
                )

        # 2. 提交Celery任务
        task = run_collector.apply_async(
            args=(source_name,),
            queue='collector',
            priority=5  # 手动触发优先级稍高
        )

        logger.info(f"【API】手动触发采集任务: {source_name}, task_id: {task.id}")

        return CollectorActionResponse(
            success=True,
            message=f"采集任务已提交到队列: {source_name}",
            task_id=task.id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发采集任务失败 {source_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"触发采集任务失败: {str(e)}"
        )


@router.get("/{source_name}/task/{task_id}")
async def get_task_status(source_name: str, task_id: str) -> Dict[str, Any]:
    """
    查询Celery任务状态

    Args:
        source_name: 消息源名称
        task_id: Celery任务ID

    Returns:
        {
            "task_id": str,
            "state": str,  # PENDING/STARTED/SUCCESS/FAILURE/RETRY
            "result": Any,
            "info": str
        }
    """
    try:
        from celery.result import AsyncResult

        task_result = AsyncResult(task_id, app=celery_app)

        response = {
            "task_id": task_id,
            "state": task_result.state,
            "result": None,
            "info": None
        }

        if task_result.state == 'SUCCESS':
            response["result"] = task_result.result
        elif task_result.state == 'FAILURE':
            response["info"] = str(task_result.info)
        elif task_result.state == 'PENDING':
            response["info"] = "任务等待执行"
        elif task_result.state == 'STARTED':
            response["info"] = "任务执行中"

        return response

    except Exception as e:
        logger.error(f"查询任务状态失败 {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"查询任务状态失败: {str(e)}"
        )


@router.get("/health")
async def collector_health_check() -> Dict[str, Any]:
    """
    采集器服务健康检查

    检查Celery worker状态
    """
    try:
        # 使用Celery Inspect API检查worker状态
        inspect = celery_app.control.inspect()

        # 获取活跃worker
        active_workers = inspect.active()
        stats = inspect.stats()

        if not active_workers or not stats:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "service": "collector",
                    "message": "没有活跃的Celery worker",
                    "timestamp": datetime.now().isoformat()
                }
            )

        return {
            "status": "healthy",
            "service": "collector",
            "workers": list(stats.keys()) if stats else [],
            "worker_count": len(stats) if stats else 0,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"采集器健康检查失败: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "collector",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )
