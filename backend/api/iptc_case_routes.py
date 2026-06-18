# -*- coding: utf-8 -*-
"""
思政课案例API路由
提供案例相关的HTTP接口
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from backend.database.connection import get_db_session
from backend.services.iptc_case_service import IPTCCaseService

router = APIRouter(prefix="/api/v1/iptc", tags=["IPTC案例"])


@router.get("/cases")
def get_cases(
    page: int = Query(1, ge=1, description="页码（从1开始）"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    knowledge_point_id: Optional[str] = Query(None, description="知识点ID过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    primary_region: Optional[str] = Query(None, description="地域过滤：上海/全国"),
    db: Session = Depends(get_db_session)
):
    """
    获取案例列表（分页）

    - **page**: 页码（从1开始）
    - **page_size**: 每页数量（1-100）
    - **knowledge_point_id**: 按知识点筛选（可选）
    - **search**: 搜索关键词（标题、内容、摘要）
    """
    try:
        result = IPTCCaseService.get_cases(
            db=db,
            page=page,
            page_size=page_size,
            knowledge_point_id=knowledge_point_id,
            search_keyword=search,
            primary_region=primary_region
        )
        # 返回符合前端ApiResponse格式
        return {
            "code": 200,
            "message": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取案例列表失败: {str(e)}")


@router.get("/cases/{case_id}")
def get_case_detail(
    case_id: str,
    db: Session = Depends(get_db_session)
):
    """
    获取单个案例详情

    - **case_id**: 案例ID
    """
    try:
        case = IPTCCaseService.get_case_by_id(db, case_id)
        if not case:
            raise HTTPException(status_code=404, detail="案例不存在")
        # 返回符合前端ApiResponse格式
        return {
            "code": 200,
            "message": "success",
            "data": case
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取案例详情失败: {str(e)}")


@router.get("/knowledge-points")
def get_knowledge_points(
    db: Session = Depends(get_db_session)
):
    """
    获取知识点列表及统计信息

    返回所有知识点，包含：
    - 关联的消息数量
    - 是否已生成案例
    - 生成的案例数量
    """
    try:
        result = IPTCCaseService.get_knowledge_points_with_stats(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识点列表失败: {str(e)}")


@router.get("/statistics")
def get_statistics(
    db: Session = Depends(get_db_session)
):
    """
    获取整体统计信息

    返回：
    - 案例总数
    - 知识点总数
    - 已生成案例的知识点数
    - 消息-知识点关联总数
    - 最近生成的案例
    """
    try:
        result = IPTCCaseService.get_statistics(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.delete("/cases/{case_id}", status_code=204)
def delete_case(
    case_id: str,
    db: Session = Depends(get_db_session)
):
    """
    删除案例

    - **case_id**: 案例ID

    成功返回HTTP 204 No Content
    案例不存在返回HTTP 404 Not Found
    """
    try:
        success = IPTCCaseService.delete_case(db, case_id)
        if not success:
            raise HTTPException(status_code=404, detail="案例不存在")
        # DELETE成功返回204 No Content，无响应体
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除案例失败: {str(e)}")
