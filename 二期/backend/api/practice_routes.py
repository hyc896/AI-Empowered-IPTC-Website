# -*- coding: utf-8 -*-

"""
实践方案相关API路由
"""

import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

logger = logging.getLogger(__name__)

from database import get_db
from services.practice_service import PracticeService
from schemas.practice import (
    PracticePlanGenerateRequest,
    PracticePlanGenerateResponse,
    TaskStatusResponse,
    PracticePlanResponse,
    PracticePlanListResponse,
    FreePlanCreateRequest
)
from api.auth_routes import get_current_user

router = APIRouter()


@router.post("/plans/generate", response_model=PracticePlanGenerateResponse, summary="生成实践方案")
def generate_plan(
    request: PracticePlanGenerateRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    生成实践方案（异步）

    - **knowledge_point_id**: 知识点ID
    - **practice_type**: 实践类型（writing/presentation/visit/performance/interaction/production/free）
    - **preferences**: 用户偏好（可选，如location、difficulty）

    返回任务ID，可通过任务ID查询生成状态
    """
    service = PracticeService(db)
    try:
        return service.generate_plan(current_user, request)
    except Exception as e:
        logger.error(f"生成方案失败: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans/task/{task_id}", response_model=TaskStatusResponse, summary="查询生成任务状态")
def get_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    查询实践方案生成任务状态

    - **task_id**: 任务ID

    返回任务状态和生成的方案（如果已完成）
    """
    service = PracticeService(db)
    return service.get_task_status(task_id)


@router.get("/plans/{plan_id}", response_model=PracticePlanResponse, summary="获取方案详情")
def get_plan(
    plan_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取实践方案详情

    - **plan_id**: 方案ID

    学生只能查看自己的方案，教师和管理员可以查看所有方案
    """
    service = PracticeService(db)
    return service.get_plan(plan_id, current_user)


@router.get("/plans", response_model=PracticePlanListResponse, summary="获取我的方案列表")
def list_my_plans(
    practice_type: Optional[str] = Query(None, description="实践类型筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取我的实践方案列表

    - **practice_type**: 实践类型筛选（可选）
    - **page**: 页码
    - **page_size**: 每页数量

    返回当前用户的所有方案
    """
    service = PracticeService(db)
    return service.list_my_plans(current_user, practice_type, page, page_size)


@router.delete("/plans/{plan_id}", summary="删除方案")
def delete_plan(
    plan_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除实践方案

    - **plan_id**: 方案ID

    学生只能删除自己的方案，管理员可以删除所有方案
    """
    service = PracticeService(db)
    return service.delete_plan(plan_id, current_user)


@router.put("/plans/{plan_id}/deadline", summary="设置方案截止日期")
def set_deadline(
    plan_id: str,
    deadline: str = Query(..., description="截止日期 (ISO格式)"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    设置实践方案截止日期

    - **plan_id**: 方案ID
    - **deadline**: 截止日期

    学生可以为自己的方案设置截止日期
    """
    service = PracticeService(db)
    return service.set_deadline(plan_id, deadline, current_user)


@router.post("/plans/free", response_model=PracticePlanResponse, summary="创建自由申请方案")
def create_free_plan(
    request: FreePlanCreateRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    学生自主创建自由申请类方案（不调用AI）

    - **knowledge_point_id**: 知识点ID
    - **title**: 方案标题
    - **description**: 方案描述
    - **expected_outcome**: 预期成果
    """
    service = PracticeService(db)
    try:
        return service.create_free_plan(current_user, request)
    except Exception as e:
        logger.error(f"创建自由方案失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
