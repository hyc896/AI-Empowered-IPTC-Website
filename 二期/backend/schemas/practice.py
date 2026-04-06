# -*- coding: utf-8 -*-

"""
实践方案相关的Pydantic Schema
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class PracticePlanGenerateRequest(BaseModel):
    """生成实践方案请求"""
    knowledge_point_id: str = Field(..., description="知识点ID")
    practice_type: str = Field(..., description="实践类型")
    preferences: Optional[Dict[str, Any]] = Field(None, description="用户偏好")
    venue_id: Optional[str] = Field(None, description="用户预选场馆ID")


class PracticePlanGenerateResponse(BaseModel):
    """生成实践方案响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    estimated_time: int = Field(..., description="预计耗时（秒）")


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    plan: Optional["PracticePlanResponse"] = None
    error_message: Optional[str] = None


class VenueInfo(BaseModel):
    """场馆信息"""
    venue_id: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None


class TaskInfo(BaseModel):
    """任务信息"""
    task: str
    description: str
    required: bool = True
    submission_requirements: Optional[List[Dict[str, Any]]] = None


class KnowledgePointBrief(BaseModel):
    """知识点简要信息"""
    id: str
    name: str
    category: str
    chapter: Optional[str] = None

    class Config:
        from_attributes = True


class PracticePlanResponse(BaseModel):
    """实践方案响应"""
    id: str
    user_id: str
    knowledge_point_id: Optional[str]
    knowledge_point: Optional[KnowledgePointBrief] = None
    practice_type: str
    title: str
    content: str
    tasks: List[TaskInfo]
    venues: Optional[List[VenueInfo]]
    venue_id: Optional[str] = None
    estimated_hours: Optional[int]
    difficulty: Optional[str]
    deadline: Optional[datetime] = None
    generation_status: str
    generated_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PracticePlanListResponse(BaseModel):
    """实践方案列表响应"""
    total: int
    items: List[PracticePlanResponse]


class FreePlanCreateRequest(BaseModel):
    """学生自主创建自由申请方案"""
    knowledge_point_id: str = Field(..., description="知识点ID")
    title: str = Field(..., description="方案标题")
    description: str = Field(..., description="方案描述")
    expected_outcome: Optional[str] = Field(None, description="预期成果")
    result_form: Optional[str] = Field(None, description="成果形式（逗号分隔）")
    class_name_id: Optional[str] = Field(None, description="班级姓名学号")
    showcase_preference: Optional[str] = Field("original", description="公众号展示偏好")
    instructor_name: Optional[str] = Field(None, description="任课教师姓名")
    completion_date: Optional[str] = Field(None, description="完成日期")
    venue_id: Optional[str] = Field(None, description="实践场馆ID")


# 更新前向引用
TaskStatusResponse.model_rebuild()
