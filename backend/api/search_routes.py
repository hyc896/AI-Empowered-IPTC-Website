# -*- coding: utf-8 -*-

"""
消息搜索API路由
提供统一的消息检索接口
"""

import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from ..services.search_service import search_service
from ..api.schemas import (
    SearchRequest, SearchResponse, MessageResponse,
    ErrorResponse
)

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/search",
    tags=["消息搜索"]
)


@router.post("/messages", response_model=SearchResponse)
async def search_messages(request: SearchRequest):
    """
    搜索消息

    支持关键词搜索和语义搜索，返回相关消息列表
    """
    try:
        start_time = datetime.now()

        # 执行搜索
        results = await search_service.search(
            source_type=request.source_type,
            query=request.query,
            time_range=request.time_range,
            limit=request.limit
        )

        # 计算搜索耗时
        search_time = (datetime.now() - start_time).total_seconds()

        # 转换结果格式
        message_responses = []
        for result in results:
            message_responses.append(MessageResponse(**result))

        return SearchResponse(
            results=message_responses,
            total=len(message_responses),
            query=request.query,
            search_time=search_time
        )

    except Exception as e:
        logger.error(f"搜索消息失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"搜索失败: {str(e)}"
        )


@router.get("/messages", response_model=List[MessageResponse])
async def get_recent_messages(
    source_type: str = None,
    limit: int = 20,
    hours: int = 24
):
    """
    获取最近消息

    获取指定时间范围内的最新消息
    """
    try:
        # 构建搜索请求
        time_range = {"hours": hours} if hours > 0 else None

        # 执行搜索（使用空查询获取所有消息）
        results = await search_service.search(
            source_type=source_type,
            query="",  # 空查询表示获取所有消息
            time_range=time_range,
            limit=limit
        )

        # 转换结果格式
        message_responses = []
        for result in results:
            message_responses.append(MessageResponse(**result))

        return message_responses

    except Exception as e:
        logger.error(f"获取最近消息失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取消息失败: {str(e)}"
        )


@router.get("/suggestions")
async def get_search_suggestions(
    q: str = "",
    limit: int = 10
):
    """
    获取搜索建议

    基于输入关键词提供搜索建议
    """
    try:
        if not q or len(q.strip()) < 2:
            return []

        # 这里可以实现搜索建议逻辑
        # 暂时返回空列表
        return []

    except Exception as e:
        logger.error(f"获取搜索建议失败: {e}", exc_info=True)
        return []


@router.get("/sources", response_model=List[str])
async def get_available_sources():
    """
    获取可用的消息源类型

    返回所有可用的消息源类别
    """
    try:
        sources = await search_service.get_sources()

        # 提取所有唯一的类别
        categories = set()
        for source in sources:
            if source.get("category"):
                categories.add(source["category"])

        return sorted(list(categories))

    except Exception as e:
        logger.error(f"获取消息源类型失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取消息源类型失败: {str(e)}"
        )


@router.get("/health")
async def search_health_check():
    """
    搜索服务健康检查

    检查搜索服务的运行状态
    """
    try:
        # 执行简单的搜索测试
        test_results = await search_service.search(
            query="test",
            limit=1
        )

        return {
            "status": "healthy",
            "service": "search",
            "timestamp": datetime.now().isoformat(),
            "test_search": "passed"
        }

    except Exception as e:
        logger.error(f"搜索服务健康检查失败: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "search",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.post("/validate")
async def validate_search_query(query: str):
    """
    验证搜索查询

    检查搜索查询是否有效
    """
    try:
        if not query or not query.strip():
            return {
                "valid": False,
                "error": "搜索关键词不能为空"
            }

        if len(query.strip()) < 2:
            return {
                "valid": False,
                "error": "搜索关键词至少需要2个字符"
            }

        if len(query.strip()) > 500:
            return {
                "valid": False,
                "error": "搜索关键词不能超过500个字符"
            }

        return {
            "valid": True,
            "message": "搜索查询有效"
        }

    except Exception as e:
        logger.error(f"验证搜索查询失败: {e}", exc_info=True)
        return {
            "valid": False,
            "error": f"验证失败: {str(e)}"
        }