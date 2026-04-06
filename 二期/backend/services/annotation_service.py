# -*- coding: utf-8 -*-

"""
批注服务
"""

import uuid
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from database.entities import SubmissionAnnotation, PracticeSubmission, User
from schemas.annotation import AnnotationCreate, AnnotationResponse, AnnotationListResponse


class AnnotationService:
    def __init__(self, db: Session):
        self.db = db

    def create_annotation(self, reviewer: User, request: AnnotationCreate) -> AnnotationResponse:
        """创建批注"""
        submission = self.db.query(PracticeSubmission).filter(
            PracticeSubmission.id == request.submission_id
        ).first()
        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交不存在")

        annotation = SubmissionAnnotation(
            id=str(uuid.uuid4()),
            submission_id=request.submission_id,
            reviewer_id=reviewer.id,
            content=request.content,
            target_text=request.target_text,
            position=request.position,
            created_at=datetime.now()
        )
        self.db.add(annotation)
        self.db.commit()
        self.db.refresh(annotation)

        return AnnotationResponse(
            id=annotation.id,
            submission_id=annotation.submission_id,
            reviewer_id=annotation.reviewer_id,
            reviewer_name=reviewer.real_name,
            content=annotation.content,
            target_text=annotation.target_text,
            position=annotation.position,
            created_at=annotation.created_at
        )

    def get_annotations(self, submission_id: str) -> AnnotationListResponse:
        """获取提交的所有批注"""
        items = self.db.query(SubmissionAnnotation).filter(
            SubmissionAnnotation.submission_id == submission_id
        ).order_by(SubmissionAnnotation.created_at).all()

        result = []
        for a in items:
            reviewer = self.db.query(User).filter(User.id == a.reviewer_id).first()
            result.append(AnnotationResponse(
                id=a.id,
                submission_id=a.submission_id,
                reviewer_id=a.reviewer_id,
                reviewer_name=reviewer.real_name if reviewer else "未知",
                content=a.content,
                target_text=a.target_text,
                position=a.position,
                created_at=a.created_at
            ))

        return AnnotationListResponse(total=len(result), items=result)

    def delete_annotation(self, annotation_id: str, reviewer: User) -> dict:
        """删除批注"""
        annotation = self.db.query(SubmissionAnnotation).filter(
            SubmissionAnnotation.id == annotation_id
        ).first()
        if not annotation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批注不存在")
        if annotation.reviewer_id != reviewer.id and reviewer.role.value != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除此批注")

        self.db.delete(annotation)
        self.db.commit()
        return {"message": "批注已删除"}
