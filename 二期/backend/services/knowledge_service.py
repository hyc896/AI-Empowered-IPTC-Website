# -*- coding: utf-8 -*-

"""
知识点服务
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from database.entities import KnowledgePoint
from schemas.knowledge import KnowledgePointCreate, KnowledgePointUpdate, KnowledgePointResponse, KnowledgePointListResponse


class KnowledgePointService:
    """知识点服务类"""

    def __init__(self, db: Session):
        self.db = db

    def create_knowledge_point(self, request: KnowledgePointCreate) -> KnowledgePointResponse:
        """创建知识点"""
        # 检查编码是否已存在
        existing = self.db.query(KnowledgePoint).filter(KnowledgePoint.code == request.code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="知识点编码已存在"
            )

        # 创建知识点
        knowledge_point = KnowledgePoint(
            id=str(uuid.uuid4()),
            code=request.code,
            name=request.name,
            category=request.category,
            chapter=request.chapter,
            description=request.description,
            keywords=request.keywords,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self.db.add(knowledge_point)
        self.db.commit()
        self.db.refresh(knowledge_point)

        return KnowledgePointResponse.from_orm(knowledge_point)

    def get_knowledge_point(self, knowledge_point_id: str) -> KnowledgePointResponse:
        """获取知识点详情"""
        knowledge_point = self.db.query(KnowledgePoint).filter(KnowledgePoint.id == knowledge_point_id).first()

        if not knowledge_point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识点不存在"
            )

        return KnowledgePointResponse.from_orm(knowledge_point)

    def list_knowledge_points(
        self,
        category: Optional[str] = None,
        chapter: Optional[str] = None,
        keyword: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20
    ) -> KnowledgePointListResponse:
        """获取知识点列表"""
        query = self.db.query(KnowledgePoint)

        # 筛选条件
        if category:
            query = query.filter(KnowledgePoint.category == category)
        if chapter:
            query = query.filter(KnowledgePoint.chapter == chapter)
        if keyword:
            query = query.filter(
                (KnowledgePoint.name.contains(keyword)) |
                (KnowledgePoint.keywords.contains(keyword))
            )
        if is_active is not None:
            query = query.filter(KnowledgePoint.is_active == is_active)

        # 总数
        total = query.count()

        # 分页
        offset = (page - 1) * page_size
        items = query.order_by(KnowledgePoint.code).offset(offset).limit(page_size).all()

        return KnowledgePointListResponse(
            total=total,
            items=[KnowledgePointResponse.from_orm(item) for item in items]
        )

    def update_knowledge_point(self, knowledge_point_id: str, request: KnowledgePointUpdate) -> KnowledgePointResponse:
        """更新知识点"""
        knowledge_point = self.db.query(KnowledgePoint).filter(KnowledgePoint.id == knowledge_point_id).first()

        if not knowledge_point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识点不存在"
            )

        # 更新字段
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(knowledge_point, field, value)

        knowledge_point.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(knowledge_point)

        return KnowledgePointResponse.from_orm(knowledge_point)

    def delete_knowledge_point(self, knowledge_point_id: str) -> dict:
        """删除知识点"""
        knowledge_point = self.db.query(KnowledgePoint).filter(KnowledgePoint.id == knowledge_point_id).first()

        if not knowledge_point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识点不存在"
            )

        self.db.delete(knowledge_point)
        self.db.commit()

        return {"message": "知识点删除成功"}
