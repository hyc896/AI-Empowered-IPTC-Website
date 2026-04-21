# -*- coding: utf-8 -*-

"""
实践提交服务
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile

from database.entities import PracticeSubmission, PracticePlan, User, SubmissionStatus, PracticeType
from schemas.submission import (
    SubmissionCreate,
    SubmissionUpdate,
    SubmissionResponse,
    SubmissionListResponse,
    FileUploadResponse
)
from services.file_service import FileService


class SubmissionService:
    """实践提交服务类"""

    def __init__(self, db: Session):
        self.db = db
        self.file_service = FileService()

    def create_submission(self, user: User, request: SubmissionCreate) -> SubmissionResponse:
        """创建提交（草稿）"""
        # 验证方案是否存在且属于当前用户
        plan = self.db.query(PracticePlan).filter(PracticePlan.id == request.plan_id).first()
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="方案不存在"
            )
        if plan.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权使用此方案"
            )

        # 创建提交
        submission = PracticeSubmission(
            id=str(uuid.uuid4()),
            plan_id=request.plan_id,
            user_id=user.id,
            practice_type=PracticeType(request.practice_type),
            title=request.title,
            content=request.content,
            reflection=request.reflection,
            files=[],
            venue_id=request.venue_id,
            completion_date=request.completion_date,
            result_form=request.result_form,
            class_name_id=request.class_name_id,
            showcase_preference=request.showcase_preference,
            instructor_name=request.instructor_name,
            status=SubmissionStatus.DRAFT,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)

        return self._to_response(submission)

    def get_submission(self, submission_id: str, user: User) -> SubmissionResponse:
        """获取提交详情"""
        submission = self.db.query(PracticeSubmission).filter(
            PracticeSubmission.id == submission_id
        ).first()

        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="提交不存在"
            )

        # 权限检查
        if submission.user_id != user.id and user.role.value not in ["teacher", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权查看此提交"
            )

        return self._to_response(submission)

    def _to_response(self, submission) -> SubmissionResponse:
        """将 ORM 对象转为响应，附带 user_name 和 review"""
        user = self.db.query(User).filter(User.id == submission.user_id).first()
        resp = SubmissionResponse.from_orm(submission)
        resp.user_name = user.real_name if user else "未知"
        # 附带审核信息
        if submission.review:
            from schemas.submission import ReviewInfo
            resp.review = ReviewInfo(
                id=submission.review.id,
                status=submission.review.status.value if hasattr(submission.review.status, 'value') else submission.review.status,
                score=submission.review.score,
                comment=submission.review.comment,
                reviewer_id=submission.review.reviewer_id,
                reviewed_at=submission.review.reviewed_at
            )
        return resp

    def update_submission(
        self,
        submission_id: str,
        user: User,
        request: SubmissionUpdate
    ) -> SubmissionResponse:
        """更新提交"""
        submission = self.db.query(PracticeSubmission).filter(
            PracticeSubmission.id == submission_id
        ).first()

        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="提交不存在"
            )

        # 权限检查
        if submission.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权修改此提交"
            )

        # 只能修改草稿状态的提交
        if submission.status != SubmissionStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只能修改草稿状态的提交"
            )

        # 更新字段
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(submission, field, value)

        submission.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(submission)

        return self._to_response(submission)

    async def upload_files(
        self,
        submission_id: str,
        user: User,
        files: List[UploadFile]
    ) -> List[FileUploadResponse]:
        """上传附件"""
        submission = self.db.query(PracticeSubmission).filter(
            PracticeSubmission.id == submission_id
        ).first()

        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="提交不存在"
            )

        # 权限检查
        if submission.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权上传文件"
            )

        # 上传文件
        uploaded_files = await self.file_service.upload_multiple_files(files)

        # 更新提交的文件列表
        current_files = submission.files or []
        current_files.extend(uploaded_files)
        submission.files = current_files
        submission.updated_at = datetime.now()

        self.db.commit()

        return [FileUploadResponse(**f) for f in uploaded_files if "error" not in f]

    def submit_for_review(self, submission_id: str, user: User) -> SubmissionResponse:
        """正式提交审核"""
        submission = self.db.query(PracticeSubmission).filter(
            PracticeSubmission.id == submission_id
        ).first()

        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="提交不存在"
            )

        # 权限检查
        if submission.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权提交此作业"
            )

        # 只能提交草稿状态的
        if submission.status != SubmissionStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只能提交草稿状态的作业"
            )

        # 更新状态
        submission.status = SubmissionStatus.SUBMITTED
        submission.submitted_at = datetime.now()
        submission.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(submission)

        return self._to_response(submission)

    def list_submissions(
        self,
        user: User,
        status_filter: Optional[str] = None,
        practice_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> SubmissionListResponse:
        """获取提交列表"""
        query = self.db.query(PracticeSubmission)

        # 学生只能看自己的，教师和管理员可以看所有
        if user.role.value == "student":
            query = query.filter(PracticeSubmission.user_id == user.id)

        # 筛选条件
        if status_filter:
            query = query.filter(PracticeSubmission.status == status_filter)
        if practice_type:
            query = query.filter(PracticeSubmission.practice_type == practice_type)

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(PracticeSubmission.created_at.desc()).offset(offset).limit(page_size).all()

        return SubmissionListResponse(
            total=total,
            items=[self._to_response(item) for item in items]
        )

    def delete_submission(self, submission_id: str, user: User) -> dict:
        """删除提交"""
        submission = self.db.query(PracticeSubmission).filter(
            PracticeSubmission.id == submission_id
        ).first()

        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="提交不存在"
            )

        # 权限检查
        if submission.user_id != user.id and user.role.value != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权删除此提交"
            )

        # 只能删除草稿状态的
        if submission.status != SubmissionStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只能删除草稿状态的提交"
            )

        # 删除关联的文件
        if submission.files:
            for file_info in submission.files:
                self.file_service.delete_file(file_info.get("path", ""))

        self.db.delete(submission)
        self.db.commit()

        return {"message": "提交删除成功"}

    def get_showcase(
        self,
        practice_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> SubmissionListResponse:
        """获取优秀作品墙"""
        query = self.db.query(PracticeSubmission).filter(
            PracticeSubmission.is_showcased == True,
            PracticeSubmission.status == SubmissionStatus.APPROVED
        )

        if practice_type:
            query = query.filter(PracticeSubmission.practice_type == practice_type)

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(PracticeSubmission.submitted_at.desc()).offset(offset).limit(page_size).all()

        return SubmissionListResponse(
            total=total,
            items=[self._to_response(item) for item in items]
        )

    def toggle_showcase(self, submission_id: str, is_showcased: bool, user: User) -> dict:
        """设置展示状态"""
        if user.role.value not in ["teacher", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )

        submission = self.db.query(PracticeSubmission).filter(
            PracticeSubmission.id == submission_id
        ).first()

        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="提交不存在"
            )

        submission.is_showcased = is_showcased
        self.db.commit()

        return {"message": "展示状态已更新"}
