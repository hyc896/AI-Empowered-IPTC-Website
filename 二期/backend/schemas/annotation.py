# -*- coding: utf-8 -*-

"""
批注相关的Pydantic Schema
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AnnotationCreate(BaseModel):
    """创建批注请求"""
    submission_id: str
    content: str
    target_text: Optional[str] = None
    position: Optional[dict] = None


class AnnotationResponse(BaseModel):
    """批注响应"""
    id: str
    submission_id: str
    reviewer_id: Optional[str]
    reviewer_name: Optional[str] = None
    content: str
    target_text: Optional[str] = None
    position: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AnnotationListResponse(BaseModel):
    """批注列表响应"""
    total: int
    items: List[AnnotationResponse]
