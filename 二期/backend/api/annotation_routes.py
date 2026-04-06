# -*- coding: utf-8 -*-

"""
批注相关API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from services.annotation_service import AnnotationService
from schemas.annotation import AnnotationCreate, AnnotationResponse, AnnotationListResponse
from api.auth_routes import get_current_user

router = APIRouter()


@router.post("", response_model=AnnotationResponse, summary="添加批注")
def create_annotation(
    request: AnnotationCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    添加批注（仅教师和管理员）

    - **submission_id**: 提交ID
    - **content**: 批注内容
    - **target_text**: 被批注的原文片段（可选）
    - **position**: 批注位置信息（可选）
    """
    if current_user.role.value not in ["teacher", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    service = AnnotationService(db)
    return service.create_annotation(current_user, request)


@router.get("/{submission_id}", response_model=AnnotationListResponse, summary="获取批注列表")
def get_annotations(
    submission_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取指定提交的所有批注

    - **submission_id**: 提交ID
    """
    service = AnnotationService(db)
    return service.get_annotations(submission_id)


@router.delete("/{annotation_id}", summary="删除批注")
def delete_annotation(
    annotation_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除批注（仅批注作者或管理员）

    - **annotation_id**: 批注ID
    """
    if current_user.role.value not in ["teacher", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    service = AnnotationService(db)
    return service.delete_annotation(annotation_id, current_user)
