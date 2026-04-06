# -*- coding: utf-8 -*-

"""
实践提交相关API路由
"""

from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List

from database import get_db
from database.entities import PracticeSubmission
from services.submission_service import SubmissionService
from services.report_service import generate_report
from schemas.submission import (
    SubmissionCreate,
    SubmissionUpdate,
    SubmissionResponse,
    SubmissionListResponse,
    FileUploadResponse
)
from api.auth_routes import get_current_user

router = APIRouter()


@router.post("", response_model=SubmissionResponse, summary="创建提交（草稿）")
def create_submission(
    request: SubmissionCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建实践提交（草稿状态）

    - **plan_id**: 方案ID
    - **practice_type**: 实践类型
    - **title**: 提交标题
    - **content**: 实践内容描述
    - **reflection**: 实践感想（可选）
    - **venue_id**: 实践场馆ID（可选）
    - **completion_date**: 完成日期（可选）

    创建后状态为draft，可以继续编辑和上传文件
    """
    service = SubmissionService(db)
    return service.create_submission(current_user, request)


@router.get("", response_model=SubmissionListResponse, summary="获取提交列表")
def list_submissions(
    status: Optional[str] = Query(None, description="状态筛选"),
    practice_type: Optional[str] = Query(None, description="实践类型筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取实践提交列表

    - **status**: 状态筛选（draft/submitted/reviewing/approved/rejected）
    - **practice_type**: 实践类型筛选
    - **page**: 页码
    - **page_size**: 每页数量

    学生只能看到自己的提交，教师和管理员可以看到所有提交
    """
    service = SubmissionService(db)
    return service.list_submissions(current_user, status, practice_type, page, page_size)


@router.get("/{submission_id}", response_model=SubmissionResponse, summary="获取提交详情")
def get_submission(
    submission_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取实践提交详情

    - **submission_id**: 提交ID

    学生只能查看自己的提交，教师和管理员可以查看所有提交
    """
    service = SubmissionService(db)
    return service.get_submission(submission_id, current_user)


@router.put("/{submission_id}", response_model=SubmissionResponse, summary="更新提交")
def update_submission(
    submission_id: str,
    request: SubmissionUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新实践提交

    - **submission_id**: 提交ID
    - 其他字段：要更新的内容

    只能更新草稿状态的提交
    """
    service = SubmissionService(db)
    return service.update_submission(submission_id, current_user, request)


@router.post("/{submission_id}/files", response_model=List[FileUploadResponse], summary="上传附件")
async def upload_files(
    submission_id: str,
    files: List[UploadFile] = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传实践提交的附件

    - **submission_id**: 提交ID
    - **files**: 文件列表

    支持的文件类型：jpg, jpeg, png, gif, mp3, mp4, pdf, doc, docx
    单个文件最大100MB
    """
    service = SubmissionService(db)
    return await service.upload_files(submission_id, current_user, files)


@router.post("/{submission_id}/submit", response_model=SubmissionResponse, summary="正式提交审核")
def submit_for_review(
    submission_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    正式提交实践作业进行审核

    - **submission_id**: 提交ID

    提交后状态变为submitted，不能再修改
    """
    service = SubmissionService(db)
    return service.submit_for_review(submission_id, current_user)


@router.get("/showcase/list", response_model=SubmissionListResponse, summary="获取优秀作品墙")
def get_showcase(
    practice_type: Optional[str] = Query(None, description="实践类型筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    获取优秀作品墙（公开接口）

    - **practice_type**: 实践类型筛选
    - **page**: 页码
    - **page_size**: 每页数量

    返回所有标记为展示的优秀作品
    """
    service = SubmissionService(db)
    return service.get_showcase(practice_type, page, page_size)


@router.get("/{submission_id}/report", summary="一键生成实践报告")
def generate_submission_report(
    submission_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    一键生成 Word 格式实践报告

    - **submission_id**: 提交ID

    根据提交内容自动生成格式化的 Word 报告文件
    """
    from fastapi import HTTPException, status
    from urllib.parse import quote

    submission = db.query(PracticeSubmission).filter(
        PracticeSubmission.id == submission_id
    ).first()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提交不存在"
        )

    if submission.user_id != current_user.id and current_user.role.value not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此提交"
        )

    buffer = generate_report(submission)
    filename = f"{submission.title or '实践报告'}.docx"
    encoded_filename = quote(filename)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
    )


@router.delete("/{submission_id}", summary="删除提交")
def delete_submission(
    submission_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除实践提交

    - **submission_id**: 提交ID

    只能删除草稿状态的提交
    """
    service = SubmissionService(db)
    return service.delete_submission(submission_id, current_user)


@router.put("/{submission_id}/showcase", summary="设置展示状态")
def toggle_showcase(
    submission_id: str,
    is_showcased: bool = Query(..., description="是否展示"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    设置提交的展示状态（仅教师和管理员）

    - **submission_id**: 提交ID
    - **is_showcased**: 是否展示在优秀作品墙

    只有教师和管理员可以设置
    """
    service = SubmissionService(db)
    return service.toggle_showcase(submission_id, is_showcased, current_user)
