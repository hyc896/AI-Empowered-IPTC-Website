# -*- coding: utf-8 -*-

"""
知识点相关的Pydantic Schema
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class KnowledgePointCreate(BaseModel):
    """创建知识点请求"""
    code: str = Field(..., description="知识点编码")
    name: str = Field(..., description="知识点名称")
    category: str = Field(..., description="所属课程（习概/思修/马原）")
    chapter: Optional[str] = Field(None, description="章节")
    description: Optional[str] = Field(None, description="知识点描述")
    keywords: Optional[str] = Field(None, description="关键词（逗号分隔）")


class KnowledgePointUpdate(BaseModel):
    """更新知识点请求"""
    name: Optional[str] = None
    category: Optional[str] = None
    chapter: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None
    is_active: Optional[bool] = None


class KnowledgePointResponse(BaseModel):
    """知识点响应"""
    id: str
    code: str
    name: str
    category: str
    chapter: Optional[str]
    description: Optional[str]
    keywords: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgePointListResponse(BaseModel):
    """知识点列表响应"""
    total: int
    items: list[KnowledgePointResponse]
