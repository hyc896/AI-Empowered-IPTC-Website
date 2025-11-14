# -*- coding: utf-8 -*-

"""
统计信息API路由
提供系统统计和性能指标
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from ..services.search_service import search_service
from ..services.collector_service import collector_service
from ..api.schemas import StatsResponse, ErrorResponse

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/stats",
    tags=["统计信息"]
)


@router.get("/overview", response_model=StatsResponse)
async def get_system_overview():
    """
    获取系统概览统计

    返回消息源、消息数量等核心统计数据
    """
    try:
        # 获取搜索服务统计
        search_stats = await search_service.get_stats()

        # 计算总数
        total_sources = search_stats.get("sources", {}).get("total", 0)
        total_messages = search_stats.get("messages", {}).get("total", 0)
        recent_total = search_stats.get("recent_messages", {}).get("total", 0)

        return StatsResponse(
            sources=search_stats.get("sources", {}),
            messages=search_stats.get("messages", {}),
            recent_messages=search_stats.get("recent_messages", {}),
            total_sources=total_sources,
            total_messages=total_messages,
            recent_total=recent_total
        )

    except Exception as e:
        logger.error(f"获取系统概览失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取系统概览失败: {str(e)}"
        )


@router.get("/sources")
async def get_source_statistics():
    """
    获取消息源统计

    返回各消息源的详细统计信息
    """
    try:
        # 获取搜索服务统计
        search_stats = await search_service.get_stats()

        return {
            "sources": search_stats.get("sources", {}),
            "active_sources": search_stats.get("sources", {}).get("active", 0),
            "inactive_sources": search_stats.get("sources", {}).get("total", 0) - search_stats.get("sources", {}).get("active", 0),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取消息源统计失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取消息源统计失败: {str(e)}"
        )


@router.get("/messages")
async def get_message_statistics(
    days: int = Query(7, ge=1, le=365, description="统计天数")
):
    """
    获取消息统计

    返回指定时间范围内的消息统计信息
    """
    try:
        # 获取搜索服务统计
        search_stats = await search_service.get_stats()

        # 这里可以实现更详细的时间范围统计
        # 暂时返回基础统计
        return {
            "messages": search_stats.get("messages", {}),
            "recent_messages": search_stats.get("recent_messages", {}),
            "days": days,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取消息统计失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取消息统计失败: {str(e)}"
        )


@router.get("/collectors")
async def get_collector_statistics():
    """
    获取采集器统计

    返回采集器的运行统计和性能指标
    """
    try:
        if not collector_service.is_running():
            return {
                "status": "stopped",
                "collectors": [],
                "total_collectors": 0,
                "running_collectors": 0,
                "failed_collectors": 0,
                "timestamp": datetime.now().isoformat()
            }

        # 获取采集器状态
        status = collector_service.get_status()
        health = await collector_service.health_check()

        # 计算统计信息
        total_collectors = len(status.get("collectors", []))
        running_collectors = health.get("healthy_collectors", 0)
        failed_collectors = total_collectors - running_collectors

        # 获取详细统计
        collector_details = []
        for collector_name in status.get("collectors", []):
            stats = collector_service.get_collector_stats(collector_name)
            collector_details.append({
                "name": collector_name,
                "success_count": stats.get("success_count", 0),
                "fail_count": stats.get("fail_count", 0),
                "last_success_time": stats.get("last_success_time"),
                "last_fail_time": stats.get("last_fail_time"),
                "last_error": stats.get("last_error"),
                "start_time": stats.get("start_time"),
                "total_runtime": stats.get("total_runtime", 0)
            })

        return {
            "status": health.get("status", "unknown"),
            "collectors": collector_details,
            "total_collectors": total_collectors,
            "running_collectors": running_collectors,
            "failed_collectors": failed_collectors,
            "startup_time": health.get("startup_time"),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取采集器统计失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取采集器统计失败: {str(e)}"
        )


@router.get("/performance")
async def get_performance_metrics():
    """
    获取性能指标

    返回系统性能相关的统计数据
    """
    try:
        # 这里可以实现性能指标收集
        # 暂时返回模拟数据
        return {
            "search_performance": {
                "average_response_time": 0.5,  # 秒
                "requests_per_minute": 10,
                "success_rate": 0.95
            },
            "collector_performance": {
                "average_collection_time": 30,  # 秒
                "collections_per_hour": 120,
                "success_rate": 0.98
            },
            "database_performance": {
                "query_time": 0.1,  # 秒
                "connection_pool_usage": 0.3,
                "slow_queries": 0
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取性能指标失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取性能指标失败: {str(e)}"
        )


@router.get("/health")
async def get_system_health():
    """
    获取系统健康状态

    返回各组件的健康检查结果
    """
    try:
        health_status = {
            "overall": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }

        # 检查数据库健康状态
        try:
            from ..database.connection import check_database_connection
            db_healthy = check_database_connection()
            health_status["components"]["database"] = {
                "status": "healthy" if db_healthy else "unhealthy",
                "message": "数据库连接正常" if db_healthy else "数据库连接失败"
            }
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "error",
                "message": f"数据库检查失败: {str(e)}"
            }

        # 检查采集器健康状态
        try:
            if collector_service.is_running():
                collector_health = await collector_service.health_check()
                health_status["components"]["collectors"] = {
                    "status": collector_health.get("status", "unknown"),
                    "healthy_collectors": collector_health.get("healthy_collectors", 0),
                    "total_collectors": collector_health.get("total_collectors", 0)
                }
            else:
                health_status["components"]["collectors"] = {
                    "status": "stopped",
                    "message": "采集器服务未运行"
                }
        except Exception as e:
            health_status["components"]["collectors"] = {
                "status": "error",
                "message": f"采集器检查失败: {str(e)}"
            }

        # 检查搜索服务健康状态
        try:
            test_search = await search_service.search(query="test", limit=1)
            health_status["components"]["search"] = {
                "status": "healthy",
                "message": "搜索服务正常"
            }
        except Exception as e:
            health_status["components"]["search"] = {
                "status": "unhealthy",
                "message": f"搜索服务异常: {str(e)}"
            }

        # 计算整体健康状态
        component_statuses = [comp.get("status") for comp in health_status["components"].values()]
        if any(status in ["unhealthy", "error"] for status in component_statuses):
            health_status["overall"] = "degraded"
        elif any(status == "stopped" for status in component_statuses):
            health_status["overall"] = "partial"

        return health_status

    except Exception as e:
        logger.error(f"获取系统健康状态失败: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "overall": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        )


@router.get("/timeline")
async def get_timeline_statistics(
    days: int = Query(7, ge=1, le=30, description="统计天数")
):
    """
    获取时间线统计

    返回按时间分布的统计数据
    """
    try:
        # 生成时间线数据点
        timeline_data = []
        end_date = datetime.now()

        for i in range(days):
            date = end_date - timedelta(days=i)
            # 这里可以实现实际的数据统计
            # 暂时返回模拟数据
            timeline_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "messages": 10 + i * 2,  # 模拟数据
                "collections": 5 + i,
                "errors": 0 if i < 3 else 1
            })

        return {
            "timeline": list(reversed(timeline_data)),
            "period_days": days,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取时间线统计失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取时间线统计失败: {str(e)}"
        )


@router.get("/categories")
async def get_category_statistics():
    """
    获取分类统计

    返回按类别的消息分布统计
    """
    try:
        # 获取搜索服务统计
        search_stats = await search_service.get_stats()

        # 这里可以实现按类别的详细统计
        # 暂时返回基础数据
        return {
            "categories": {
                "news": {
                    "total": search_stats.get("messages", {}).get("tonghuashun", 0) +
                           search_stats.get("messages", {}).get("kr36", 0),
                    "sources": 2,
                    "last_24h": search_stats.get("recent_messages", {}).get("tonghuashun", 0) +
                               search_stats.get("recent_messages", {}).get("kr36", 0)
                },
                "academic": {
                    "total": search_stats.get("messages", {}).get("arxiv", 0),
                    "sources": 1,
                    "last_24h": search_stats.get("recent_messages", {}).get("arxiv", 0)
                }
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取分类统计失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取分类统计失败: {str(e)}"
        )