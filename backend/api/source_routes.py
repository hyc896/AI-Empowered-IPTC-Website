# -*- coding: utf-8 -*-

"""
消息源管理API路由
提供消息源的增删改查功能
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from ..database.connection import create_session
from ..database.entities import MessageSource
from ..api.schemas import (
    MessageSourceResponse, MessageSourceCreate, MessageSourceUpdate,
    ErrorResponse, SuccessResponse
)
from ..services.cache_service import cache_service

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/sources",
    tags=["消息源管理"]
)


@router.get("", response_model=List[MessageSourceResponse])
async def get_sources(
    is_active: Optional[bool] = Query(None, description="是否启用"),
    category: Optional[str] = Query(None, description="消息源类别")
):
    """
    获取消息源列表

    支持按状态和类别过滤
    """
    # 尝试从缓存获取
    cached = cache_service.get_sources(category=category, is_active=is_active)
    if cached:
        logger.info(f"【消息源列表】缓存命中，返回 {len(cached)} 个消息源")
        return [MessageSourceResponse(**s) for s in cached]

    try:
        with create_session() as db:
            query = db.query(MessageSource)

            # 应用过滤条件
            if is_active is not None:
                query = query.filter(MessageSource.is_active == is_active)

            if category:
                query = query.filter(MessageSource.category == category)

            # 执行查询
            sources = query.order_by(MessageSource.created_at.desc()).all()

            # 转换为响应格式
            result = [MessageSourceResponse.from_orm(source) for source in sources]

            # 缓存结果
            cache_data = [s.dict() for s in result]
            cache_service.set_sources(cache_data, category=category, is_active=is_active)
            logger.info(f"【消息源列表】结果已缓存，共 {len(result)} 个消息源")

            return result

    except Exception as e:
        logger.error(f"获取消息源列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取消息源列表失败: {str(e)}"
        )


@router.get("/{source_id}", response_model=MessageSourceResponse)
async def get_source(source_id: str):
    """
    获取指定消息源详情

    根据ID获取单个消息源的详细信息
    """
    try:
        with create_session() as db:
            source = db.query(MessageSource).filter(MessageSource.id == source_id).first()

            if not source:
                raise HTTPException(
                    status_code=404,
                    detail=f"消息源 {source_id} 不存在"
                )

            return MessageSourceResponse.from_orm(source)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取消息源详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取消息源详情失败: {str(e)}"
        )


@router.post("/", response_model=MessageSourceResponse, status_code=201)
async def create_source(source_data: MessageSourceCreate):
    """
    创建新消息源

    添加新的消息源配置
    """
    try:
        with create_session() as db:
            # 检查名称是否已存在
            existing = db.query(MessageSource).filter(MessageSource.name == source_data.name).first()
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"消息源名称 {source_data.name} 已存在"
                )

            # 创建新的消息源
            new_source = MessageSource(
                id=str(uuid.uuid4()),
                name=source_data.name,
                adapter_name=source_data.adapter_name,
                category=source_data.category,
                display_name=source_data.display_name,
                config=source_data.config,
                schedule=source_data.schedule,
                is_active=source_data.is_active,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            db.add(new_source)
            db.commit()
            db.refresh(new_source)

            logger.info(f"创建消息源成功: {new_source.name} ({new_source.id})")

            # 使消息源缓存失效
            cache_service.invalidate_sources()

            return MessageSourceResponse.from_orm(new_source)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建消息源失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"创建消息源失败: {str(e)}"
        )


@router.put("/{source_id}", response_model=MessageSourceResponse)
async def update_source(source_id: str, source_data: MessageSourceUpdate):
    """
    更新消息源

    更新指定消息源的配置信息
    """
    try:
        with create_session() as db:
            source = db.query(MessageSource).filter(MessageSource.id == source_id).first()

            if not source:
                raise HTTPException(
                    status_code=404,
                    detail=f"消息源 {source_id} 不存在"
                )

            # 更新字段
            update_data = source_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(source, field, value)

            source.updated_at = datetime.now()
            db.commit()
            db.refresh(source)

            logger.info(f"更新消息源成功: {source.name} ({source.id})")

            # 使消息源缓存失效
            cache_service.invalidate_sources()

            return MessageSourceResponse.from_orm(source)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新消息源失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"更新消息源失败: {str(e)}"
        )


@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: str):
    """
    删除消息源

    删除指定的消息源（级联删除相关消息）
    """
    try:
        with create_session() as db:
            source = db.query(MessageSource).filter(MessageSource.id == source_id).first()

            if not source:
                raise HTTPException(
                    status_code=404,
                    detail=f"消息源 {source_id} 不存在"
                )

            # 删除消息源（级联删除相关消息）
            db.delete(source)
            db.commit()

            logger.info(f"删除消息源成功: {source.name} ({source.id})")

            # 使消息源缓存失效
            cache_service.invalidate_sources()

            return None  # HTTP 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除消息源失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"删除消息源失败: {str(e)}"
        )


@router.post("/{source_id}/activate", response_model=SuccessResponse)
async def activate_source(source_id: str):
    """
    启用消息源

    启用指定消息源的采集功能
    """
    try:
        with create_session() as db:
            source = db.query(MessageSource).filter(MessageSource.id == source_id).first()

            if not source:
                raise HTTPException(
                    status_code=404,
                    detail=f"消息源 {source_id} 不存在"
                )

            source.is_active = True
            source.updated_at = datetime.now()
            db.commit()

            logger.info(f"启用消息源成功: {source.name} ({source.id})")

            # 使消息源缓存失效
            cache_service.invalidate_sources()

            return SuccessResponse(
                message=f"消息源 {source.name} 已启用"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启用消息源失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"启用消息源失败: {str(e)}"
        )


@router.post("/{source_id}/deactivate", response_model=SuccessResponse)
async def deactivate_source(source_id: str):
    """
    禁用消息源

    禁用指定消息源的采集功能
    """
    try:
        with create_session() as db:
            source = db.query(MessageSource).filter(MessageSource.id == source_id).first()

            if not source:
                raise HTTPException(
                    status_code=404,
                    detail=f"消息源 {source_id} 不存在"
                )

            source.is_active = False
            source.updated_at = datetime.now()
            db.commit()

            logger.info(f"禁用消息源成功: {source.name} ({source.id})")

            # 使消息源缓存失效
            cache_service.invalidate_sources()

            return SuccessResponse(
                message=f"消息源 {source.name} 已禁用"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"禁用消息源失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"禁用消息源失败: {str(e)}"
        )


@router.get("/{source_id}/status")
async def get_source_status(source_id: str):
    """
    获取消息源状态

    获取指定消息源的详细状态信息
    """
    try:
        with create_session() as db:
            source = db.query(MessageSource).filter(MessageSource.id == source_id).first()

            if not source:
                raise HTTPException(
                    status_code=404,
                    detail=f"消息源 {source_id} 不存在"
                )

            # 获取消息统计
            stats = await get_source_statistics(source_id)

            return {
                "id": source.id,
                "name": source.name,
                "display_name": source.display_name,
                "category": source.category,
                "is_active": source.is_active,
                "last_crawled_at": source.last_crawled_at,
                "created_at": source.created_at,
                "updated_at": source.updated_at,
                "statistics": stats
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取消息源状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取消息源状态失败: {str(e)}"
        )


async def get_source_statistics(source_id: str) -> dict:
    """获取消息源的统计信息"""
    try:
        # 这里可以实现统计信息的计算逻辑
        # 暂时返回空统计
        return {
            "total_messages": 0,
            "recent_messages": 0,
            "last_message_time": None
        }
    except Exception as e:
        logger.error(f"获取消息源统计失败: {e}")
        return {}


@router.get("/categories", response_model=List[str])
async def get_source_categories():
    """
    获取所有消息源类别

    返回系统中所有可用的消息源类别
    """
    try:
        with create_session() as db:
            categories = db.query(MessageSource.category).distinct().all()

            # 过滤空值并提取类别
            category_list = []
            for (category,) in categories:
                if category:
                    category_list.append(category)

            return sorted(category_list)

    except Exception as e:
        logger.error(f"获取消息源类别失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取消息源类别失败: {str(e)}"
        )


@router.post("/validate-config")
async def validate_source_config(config: dict):
    """
    验证消息源配置

    检查消息源配置是否有效
    """
    try:
        # 基础配置验证
        required_fields = ["name", "adapter_name"]
        missing_fields = []

        for field in required_fields:
            if field not in config or not config[field]:
                missing_fields.append(field)

        if missing_fields:
            return {
                "valid": False,
                "error": f"缺少必需字段: {', '.join(missing_fields)}"
            }

        # 检查名称长度
        if len(config["name"]) > 100:
            return {
                "valid": False,
                "error": "消息源名称不能超过100个字符"
            }

        # 检查适配器名称
        if len(config["adapter_name"]) > 100:
            return {
                "valid": False,
                "error": "适配器名称不能超过100个字符"
            }

        return {
            "valid": True,
            "message": "配置验证通过"
        }

    except Exception as e:
        logger.error(f"验证消息源配置失败: {e}", exc_info=True)
        return {
            "valid": False,
            "error": f"验证失败: {str(e)}"
        }