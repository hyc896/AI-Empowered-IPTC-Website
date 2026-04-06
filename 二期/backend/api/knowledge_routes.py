# -*- coding: utf-8 -*-

"""
知识点相关API路由
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from services.knowledge_service import KnowledgePointService
from schemas.knowledge import KnowledgePointCreate, KnowledgePointUpdate, KnowledgePointResponse, KnowledgePointListResponse
from api.auth_routes import get_current_user

router = APIRouter()


@router.post("", response_model=KnowledgePointResponse, summary="创建知识点")
def create_knowledge_point(
    request: KnowledgePointCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建知识点（仅管理员和教师）
    """
    if current_user.role.value not in ["admin", "teacher"]:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")

    service = KnowledgePointService(db)
    return service.create_knowledge_point(request)


@router.get("", response_model=KnowledgePointListResponse, summary="获取知识点列表")
def list_knowledge_points(
    category: Optional[str] = Query(None, description="课程类别"),
    chapter: Optional[str] = Query(None, description="章节"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    获取知识点列表（支持筛选和分页）
    """
    service = KnowledgePointService(db)
    return service.list_knowledge_points(category, chapter, keyword, is_active, page, page_size)


@router.get("/{knowledge_point_id}", response_model=KnowledgePointResponse, summary="获取知识点详情")
def get_knowledge_point(
    knowledge_point_id: str,
    db: Session = Depends(get_db)
):
    """
    获取知识点详情
    """
    service = KnowledgePointService(db)
    return service.get_knowledge_point(knowledge_point_id)


@router.put("/{knowledge_point_id}", response_model=KnowledgePointResponse, summary="更新知识点")
def update_knowledge_point(
    knowledge_point_id: str,
    request: KnowledgePointUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新知识点（仅管理员和教师）
    """
    if current_user.role.value not in ["admin", "teacher"]:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")

    service = KnowledgePointService(db)
    return service.update_knowledge_point(knowledge_point_id, request)


@router.delete("/{knowledge_point_id}", summary="删除知识点")
def delete_knowledge_point(
    knowledge_point_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除知识点（仅管理员）
    """
    if current_user.role.value != "admin":
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")

    service = KnowledgePointService(db)
    return service.delete_knowledge_point(knowledge_point_id)
