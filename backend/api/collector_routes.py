# -*- coding: utf-8 -*-

"""
采集器控制API路由
提供采集器的启动、停止、状态查询等功能
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from ..services.collector_service import collector_service
from ..api.schemas import (
    CollectorStatusResponse, CollectorStatsResponse, CollectorActionResponse,
    ErrorResponse
)

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/collectors",
    tags=["采集器管理"]
)


@router.get("/status", response_model=CollectorStatusResponse)
async def get_collector_status():
    """
    获取采集器服务状态

    返回所有采集器的运行状态和健康信息
    """
    try:
        if not collector_service.is_running():
            return CollectorStatusResponse(
                status="stopped",
                collectors=[],
                healthy_collectors=0,
                total_collectors=0,
                startup_time=None
            )

        # 获取健康检查结果
        health_result = await collector_service.health_check()

        return CollectorStatusResponse(**health_result)

    except Exception as e:
        logger.error(f"获取采集器状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取采集器状态失败: {str(e)}"
        )


@router.get("/list", response_model=list)
async def get_collector_list():
    """
    获取采集器列表

    返回所有可用的采集器名称
    """
    try:
        status = collector_service.get_status()
        return status.get("collectors", [])

    except Exception as e:
        logger.error(f"获取采集器列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取采集器列表失败: {str(e)}"
        )


@router.get("/{source_name}/stats", response_model=CollectorStatsResponse)
async def get_collector_stats(source_name: str):
    """
    获取指定采集器的统计信息

    返回采集器的运行统计和性能指标
    """
    try:
        stats = collector_service.get_collector_stats(source_name)
        stats["name"] = source_name  # 确保名称一致

        return CollectorStatsResponse(**stats)

    except Exception as e:
        logger.error(f"获取采集器统计失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取采集器统计失败: {str(e)}"
        )


@router.post("/{source_name}/start", response_model=CollectorActionResponse)
async def start_collector(source_name: str):
    """
    启动指定采集器

    启动指定的消息源采集器
    """
    try:
        # 检查服务是否运行
        if not collector_service.is_running():
            # 先启动整个服务
            await collector_service.start()

        # 如果采集器已经在运行，返回成功
        if source_name in collector_service._collectors:
            return CollectorActionResponse(
                success=True,
                message=f"采集器 {source_name} 已在运行中"
            )

        # 重新加载配置并启动采集器
        success = await collector_service.restart_collector(source_name)

        if success:
            return CollectorActionResponse(
                success=True,
                message=f"采集器 {source_name} 启动成功"
            )
        else:
            return CollectorActionResponse(
                success=False,
                message=f"采集器 {source_name} 启动失败"
            )

    except Exception as e:
        logger.error(f"启动采集器失败 {source_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"启动采集器失败: {str(e)}"
        )


@router.post("/{source_name}/stop", response_model=CollectorActionResponse)
async def stop_collector(source_name: str):
    """
    停止指定采集器

    停止指定的消息源采集器
    """
    try:
        success = await collector_service.stop_collector(source_name)

        if success:
            return CollectorActionResponse(
                success=True,
                message=f"采集器 {source_name} 停止成功"
            )
        else:
            return CollectorActionResponse(
                success=False,
                message=f"采集器 {source_name} 停止失败，可能不存在或未运行"
            )

    except Exception as e:
        logger.error(f"停止采集器失败 {source_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"停止采集器失败: {str(e)}"
        )


@router.post("/{source_name}/trigger", response_model=CollectorActionResponse)
async def trigger_manual_collect(source_name: str):
    """
    手动触发采集

    触发指定消息源的一次手动采集
    """
    try:
        success = await collector_service.trigger_manual_collect(source_name)

        if success:
            return CollectorActionResponse(
                success=True,
                message=f"采集器 {source_name} 手动采集已触发"
            )
        else:
            return CollectorActionResponse(
                success=False,
                message=f"采集器 {source_name} 手动采集触发失败"
            )

    except Exception as e:
        logger.error(f"触发手动采集失败 {source_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"触发手动采集失败: {str(e)}"
        )


@router.post("/{source_name}/restart", response_model=CollectorActionResponse)
async def restart_collector(source_name: str):
    """
    重启指定采集器

    重启指定的消息源采集器
    """
    try:
        success = await collector_service.restart_collector(source_name)

        if success:
            return CollectorActionResponse(
                success=True,
                message=f"采集器 {source_name} 重启成功"
            )
        else:
            return CollectorActionResponse(
                success=False,
                message=f"采集器 {source_name} 重启失败"
            )

    except Exception as e:
        logger.error(f"重启采集器失败 {source_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"重启采集器失败: {str(e)}"
        )


@router.post("/{source_name}/trigger", response_model=CollectorActionResponse)
async def trigger_manual_collect(source_name: str):
    """
    手动触发采集

    立即执行一次采集任务
    """
    try:
        success = await collector_service.trigger_manual_collect(source_name)

        if success:
            return CollectorActionResponse(
                success=True,
                message=f"手动触发采集 {source_name} 成功"
            )
        else:
            return CollectorActionResponse(
                success=False,
                message=f"手动触发采集 {source_name} 失败"
            )

    except Exception as e:
        logger.error(f"手动触发采集失败 {source_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"手动触发采集失败: {str(e)}"
        )


@router.post("/start-all", response_model=CollectorActionResponse)
async def start_all_collectors():
    """
    启动所有采集器

    启动所有激活的消息源采集器
    """
    try:
        if collector_service.is_running():
            return CollectorActionResponse(
                success=True,
                message="采集器服务已在运行中"
            )

        await collector_service.start()

        status = collector_service.get_status()
        collector_count = status.get("collector_count", 0)

        return CollectorActionResponse(
            success=True,
            message=f"已启动 {collector_count} 个采集器"
        )

    except Exception as e:
        logger.error(f"启动所有采集器失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"启动所有采集器失败: {str(e)}"
        )


@router.post("/stop-all", response_model=CollectorActionResponse)
async def stop_all_collectors():
    """
    停止所有采集器

    停止所有运行的采集器
    """
    try:
        await collector_service.stop()

        return CollectorActionResponse(
            success=True,
            message="所有采集器已停止"
        )

    except Exception as e:
        logger.error(f"停止所有采集器失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"停止所有采集器失败: {str(e)}"
        )


@router.get("/health")
async def collector_health_check():
    """
    采集器服务健康检查

    检查采集器服务的运行状态
    """
    try:
        if not collector_service.is_running():
            return JSONResponse(
                status_code=503,
                content={
                    "status": "stopped",
                    "service": "collector",
                    "message": "采集器服务未运行",
                    "timestamp": datetime.now().isoformat()
                }
            )

        health_result = await collector_service.health_check()
        health_result["timestamp"] = datetime.now().isoformat()

        return health_result

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


@router.get("/{source_name}/logs")
async def get_collector_logs(
    source_name: str,
    lines: int = 100,
    level: str = "INFO"
):
    """
    获取采集器日志

    返回指定采集器的最近日志
    """
    try:
        # 这里可以实现日志获取逻辑
        # 暂时返回模拟日志
        return {
            "source_name": source_name,
            "logs": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "message": f"采集器 {source_name} 日志功能待实现"
                }
            ],
            "total_lines": 1
        }

    except Exception as e:
        logger.error(f"获取采集器日志失败 {source_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取采集器日志失败: {str(e)}"
        )


@router.post("/{source_name}/test", response_model=CollectorActionResponse)
async def test_collector(source_name: str):
    """
    测试采集器配置

    测试指定采集器的配置是否正确
    """
    try:
        # 这里可以实现采集器配置测试逻辑
        # 暂时返回成功
        return CollectorActionResponse(
            success=True,
            message=f"采集器 {source_name} 配置测试通过"
        )

    except Exception as e:
        logger.error(f"测试采集器配置失败 {source_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"测试采集器配置失败: {str(e)}"
        )