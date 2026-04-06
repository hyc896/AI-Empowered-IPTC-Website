# -*- coding: utf-8 -*-

"""
审核相关的Pydantic Schema
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ReviewCreate(BaseModel):
    """创建审核请求"""
    submission_id: str = Field(..., description="提交ID")
    status: str = Field(..., description="审核结果（approved/rejected）")
    score: Optional[int] = Field(None, ge=0, le=100, description="评分（0-100）")
    comment: Optional[str] = Field(None, description="评语")


class ReviewResponse(BaseModel):
    """审核响应"""
    id: str
    submission_id: str
    reviewer_id: str
    status: str
    score: Optional[int]
    comment: Optional[str]
    reviewed_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewListResponse(BaseModel):
    """审核列表响应"""
    total: int
    items: List[ReviewResponse]


class PendingSubmissionResponse(BaseModel):
    """待审核提交响应"""
    id: str
    plan_id: str
    user_id: str
    user_name: str
    class_name: Optional[str] = None
    practice_type: str
    title: str
    submitted_at: datetime

    class Config:
        from_attributes = True


class PendingSubmissionListResponse(BaseModel):
    """待审核列表响应"""
    total: int
    items: List[PendingSubmissionResponse]
