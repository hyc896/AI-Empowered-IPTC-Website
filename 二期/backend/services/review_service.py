# -*- coding: utf-8 -*-

"""
审核服务
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from database.entities import PracticeReview, PracticeSubmission, User, SubmissionStatus
from schemas.review import (
    ReviewCreate,
    ReviewResponse,
    ReviewListResponse,
    PendingSubmissionResponse,
    PendingSubmissionListResponse
)


class ReviewService:
    """审核服务类"""

    def __init__(self, db: Session):
        self.db = db

    def create_review(self, reviewer: User, request: ReviewCreate) -> ReviewResponse:
        """
        创建审核

        Args:
            reviewer: 审核教师
            request: 审核请求

        Returns:
            审核响应
        """
        # 验证提交是否存在
        submission = self.db.query(PracticeSubmission).filter(
            PracticeSubmission.id == request.submission_id
        ).first()

        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="提交不存在"
            )

        # 验证提交状态
        if submission.status not in [SubmissionStatus.SUBMITTED, SubmissionStatus.REVIEWING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只能审核已提交的作业"
            )

        # 检查是否已经审核过
        existing_review = self.db.query(PracticeReview).filter(
            PracticeReview.submission_id == request.submission_id
        ).first()

        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该提交已经审核过"
            )

        # 创建审核记录
        review = PracticeReview(
            id=str(uuid.uuid4()),
            submission_id=request.submission_id,
            reviewer_id=reviewer.id,
            status=SubmissionStatus(request.status),
            score=request.score,
            comment=request.comment,
            reviewed_at=datetime.now(),
            created_at=datetime.now()
        )

        self.db.add(review)

        # 更新提交状态
        submission.status = SubmissionStatus(request.status)
        submission.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(review)

        return ReviewResponse.from_orm(review)

    def get_pending_submissions(
        self,
        reviewer: User,
        practice_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None
    ) -> PendingSubmissionListResponse:
        """
        获取待审核列表（教师只看到自己班级学生的提交）
        """
        query = self.db.query(PracticeSubmission).filter(
            PracticeSubmission.status == SubmissionStatus.SUBMITTED
        )

        # 教师只看到自己关联学生的提交，管理员看全部
        if reviewer.role.value == "teacher":
            student_ids = [
                s.id for s in self.db.query(User.id).filter(User.teacher_id == reviewer.id).all()
            ]
            query = query.filter(PracticeSubmission.user_id.in_(student_ids))

        # 按学生姓名搜索
        if keyword:
            matching_user_ids = [
                u.id for u in self.db.query(User.id).filter(User.real_name.like(f"%{keyword}%")).all()
            ]
            query = query.filter(PracticeSubmission.user_id.in_(matching_user_ids))

        if practice_type:
            query = query.filter(PracticeSubmission.practice_type == practice_type)

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(PracticeSubmission.submitted_at).offset(offset).limit(page_size).all()

        # 构建响应
        pending_items = []
        for item in items:
            user = self.db.query(User).filter(User.id == item.user_id).first()
            pending_items.append(
                PendingSubmissionResponse(
                    id=item.id,
                    plan_id=item.plan_id,
                    user_id=item.user_id,
                    user_name=user.real_name if user else "未知",
                    class_name=user.class_name if user else "",
                    practice_type=item.practice_type.value,
                    title=item.title,
                    submitted_at=item.submitted_at
                )
            )

        return PendingSubmissionListResponse(
            total=total,
            items=pending_items
        )

    def get_review_history(
        self,
        reviewer: User,
        page: int = 1,
        page_size: int = 20
    ) -> ReviewListResponse:
        """
        获取审核历史

        Args:
            reviewer: 审核教师
            page: 页码
            page_size: 每页数量

        Returns:
            审核历史列表
        """
        query = self.db.query(PracticeReview).filter(
            PracticeReview.reviewer_id == reviewer.id
        )

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(PracticeReview.reviewed_at.desc()).offset(offset).limit(page_size).all()

        return ReviewListResponse(
            total=total,
            items=[ReviewResponse.from_orm(item) for item in items]
        )

    def get_review(self, review_id: str) -> ReviewResponse:
        """
        获取审核详情

        Args:
            review_id: 审核ID

        Returns:
            审核详情
        """
        review = self.db.query(PracticeReview).filter(PracticeReview.id == review_id).first()

        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="审核记录不存在"
            )

        return ReviewResponse.from_orm(review)

    def get_statistics(self, reviewer: User) -> dict:
        """
        获取审核统计数据

        Args:
            reviewer: 审核教师

        Returns:
            统计数据
        """
        # 教师只统计自己学生的提交
        if reviewer.role.value == "teacher":
            student_ids = [
                s.id for s in self.db.query(User.id).filter(User.teacher_id == reviewer.id).all()
            ]
            base_query = self.db.query(PracticeSubmission).filter(
                PracticeSubmission.user_id.in_(student_ids)
            )
        else:
            base_query = self.db.query(PracticeSubmission)

        pending = base_query.filter(PracticeSubmission.status == SubmissionStatus.SUBMITTED).count()
        approved = base_query.filter(PracticeSubmission.status == SubmissionStatus.APPROVED).count()
        rejected = base_query.filter(PracticeSubmission.status == SubmissionStatus.REJECTED).count()

        return {
            "pending": pending,
            "approved": approved,
            "rejected": rejected
        }
