# -*- coding: utf-8 -*-

"""
审核相关API路由
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from services.review_service import ReviewService
from schemas.review import (
    ReviewCreate,
    ReviewResponse,
    ReviewListResponse,
    PendingSubmissionListResponse
)
from api.auth_routes import get_current_user

router = APIRouter()


@router.get("/pending", response_model=PendingSubmissionListResponse, summary="获取待审核列表")
def get_pending_submissions(
    practice_type: Optional[str] = Query(None, description="实践类型筛选"),
    keyword: Optional[str] = Query(None, description="搜索学生姓名"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取待审核的实践提交列表（仅教师和管理员）

    - **practice_type**: 实践类型筛选（可选）
    - **keyword**: 搜索学生姓名（可选）
    - **page**: 页码
    - **page_size**: 每页数量

    返回所有状态为submitted的提交
    """
    # 权限检查
    if current_user.role.value not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    service = ReviewService(db)
    return service.get_pending_submissions(current_user, practice_type, page, page_size, keyword)


@router.post("", response_model=ReviewResponse, summary="提交审核结果")
def create_review(
    request: ReviewCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    提交审核结果（仅教师和管理员）

    - **submission_id**: 提交ID
    - **status**: 审核结果（approved/rejected）
    - **score**: 评分（0-100，可选）
    - **comment**: 评语（可选）

    审核后提交状态会更新为approved或rejected
    """
    # 权限检查
    if current_user.role.value not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    service = ReviewService(db)
    return service.create_review(current_user, request)


@router.get("/history", response_model=ReviewListResponse, summary="获取审核历史")
def get_review_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取我的审核历史（仅教师和管理员）

    - **page**: 页码
    - **page_size**: 每页数量

    返回当前教师的所有审核记录
    """
    # 权限检查
    if current_user.role.value not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    service = ReviewService(db)
    return service.get_review_history(current_user, page, page_size)


@router.get("/stats/summary", summary="获取审核统计")
def get_statistics(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取审核统计数据（仅教师和管理员）

    返回待审核、已通过、未通过的数量
    """
    # 权限检查
    if current_user.role.value not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    service = ReviewService(db)
    return service.get_statistics(current_user)


@router.get("/ai-suggest/{submission_id}", summary="获取AI评分建议")
def get_ai_suggestion(
    submission_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取AI辅助评分建议（仅教师和管理员）"""
    if current_user.role.value not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )
    from services.ai_grading_service import AIGradingService
    service = AIGradingService(db)
    return service.get_ai_suggestion(submission_id)


@router.get("/{review_id}", response_model=ReviewResponse, summary="获取审核详情")
def get_review(
    review_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取审核详情

    - **review_id**: 审核ID

    教师和管理员可以查看所有审核记录
    """
    # 权限检查
    if current_user.role.value not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    service = ReviewService(db)
    return service.get_review(review_id)
