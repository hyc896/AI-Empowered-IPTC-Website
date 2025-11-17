# -*- coding: utf-8 -*-
"""
SSE（Server-Sent Events）推送服务

功能：
1. 实时推送新增AI消息到前端
2. 自动心跳保活（30秒）
3. 优雅断开与资源清理
4. 支持多客户端并发连接
5. 提供历史AI标签消息查询
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Request, Query
from fastapi.responses import StreamingResponse
from backend.services.event_bus import get_event_bus
from backend.database.connection import create_session
from backend.database.entities import TongHuaShunMessage, Kr36Message
from sqlalchemy import or_

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/events/ai-tags/stream")
async def stream_ai_tags(request: Request):
    """
    SSE流端点：实时推送新增的AI标签消息

    工作流程：
    1. 客户端连接时订阅EventBus
    2. 收到事件后立即推送给客户端
    3. 每30秒发送心跳（防止连接超时）
    4. 客户端断开时自动清理资源

    SSE格式：
    data: {"ai_tag": "AI治理信息", "title": "...", ...}

    """
    event_bus = get_event_bus()
    queue = None
    client_id = id(request)  # 客户端唯一标识

    async def event_generator():
        nonlocal queue

        try:
            # 订阅事件总线
            queue = await event_bus.subscribe("new_ai_message", maxsize=100)
            logger.info(f"SSE客户端已连接: {client_id}")

            while True:
                # 检查客户端是否断开
                if await request.is_disconnected():
                    logger.info(f"SSE客户端已断开: {client_id}")
                    break

                try:
                    # 等待事件（带超时，用于发送心跳）
                    event_data = await asyncio.wait_for(queue.get(), timeout=30)

                    # 构造SSE消息
                    sse_message = f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    yield sse_message

                except asyncio.TimeoutError:
                    # 超时则发送心跳（保持连接活跃）
                    yield ": heartbeat\n\n"

        except asyncio.CancelledError:
            logger.info(f"SSE连接被取消: {client_id}")
        except Exception as e:
            logger.error(f"SSE流异常: {e}", exc_info=True)
        finally:
            # 清理资源
            if queue:
                await event_bus.unsubscribe("new_ai_message", queue)
            logger.info(f"SSE资源已清理: {client_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
        }
    )


@router.get("/events/stats")
async def get_event_stats():
    """
    获取事件总线统计信息（监控端点）

    返回：
    - 各事件类型的订阅者数量
    - 用于健康检查和调试
    """
    event_bus = get_event_bus()
    stats = event_bus.get_all_stats()

    return {
        "stats": stats,
        "new_ai_message_subscribers": stats.get("new_ai_message", 0),
        "total_subscribers": sum(stats.values())
    }


@router.get("/events/ai-tags/recent")
async def get_recent_ai_tags(
    limit: int = Query(100, ge=10, le=500, description="每个标签最多返回N条消息"),
    hours: Optional[int] = Query(24, ge=1, le=8760, description="时间范围（小时），不传或传0表示不限制")
):
    """
    获取最近的AI标签消息（用于页面初始化）

    Args:
        limit: 每个标签最多返回N条（默认100条）
        hours: 时间范围（默认24小时），传0或null表示查询所有历史

    Returns:
        {
            "AI治理信息": [...],
            "AI科研信息": [...],
            "AI产业信息": [...]
        }
    """
    try:
        result = {
            "AI治理信息": [],
            "AI科研信息": [],
            "AI产业信息": []
        }

        # 计算时间截止点（如果hours为0或None，则不限制）
        cutoff_time = None
        if hours and hours > 0:
            cutoff_time = datetime.now() - timedelta(hours=hours)

        with create_session() as db:
            # 为每个AI标签分别查询，确保每个标签都能获取到数据
            for tag in ["AI治理信息", "AI科研信息", "AI产业信息"]:
                # 查询同花顺消息
                ths_query = db.query(TongHuaShunMessage).filter(
                    TongHuaShunMessage.ai_tag == tag
                )
                if cutoff_time:
                    ths_query = ths_query.filter(TongHuaShunMessage.crawled_at >= cutoff_time)
                ths_msgs = ths_query.order_by(TongHuaShunMessage.crawled_at.desc()).limit(limit).all()

                for msg in ths_msgs:
                    result[tag].append({
                        "message_id": msg.id,
                        "title": msg.title,
                        "summary": msg.summary or msg.content[:200],
                        "ai_tag": msg.ai_tag,
                        "source_name": "同花顺快讯",
                        "timestamp": msg.crawled_at.isoformat()
                    })

                # 查询36氪消息
                kr36_query = db.query(Kr36Message).filter(
                    Kr36Message.ai_tag == tag
                )
                if cutoff_time:
                    kr36_query = kr36_query.filter(Kr36Message.crawled_at >= cutoff_time)
                kr36_msgs = kr36_query.order_by(Kr36Message.crawled_at.desc()).limit(limit).all()

                for msg in kr36_msgs:
                    result[tag].append({
                        "message_id": msg.id,
                        "title": msg.title,
                        "summary": msg.summary or msg.content[:200],
                        "ai_tag": msg.ai_tag,
                        "source_name": "36氪快讯",
                        "timestamp": msg.crawled_at.isoformat()
                    })

                # 按时间排序并限制数量
                result[tag] = sorted(result[tag], key=lambda x: x['timestamp'], reverse=True)[:limit]

        time_range_desc = f"{hours}小时" if cutoff_time else "所有历史"
        logger.info(
            f"返回AI标签消息（{time_range_desc}）: "
            f"治理={len(result['AI治理信息'])}, "
            f"科研={len(result['AI科研信息'])}, "
            f"产业={len(result['AI产业信息'])}"
        )

        return result

    except Exception as e:
        logger.error(f"获取AI标签消息失败: {e}", exc_info=True)
        return {
            "AI治理信息": [],
            "AI科研信息": [],
            "AI产业信息": []
        }
