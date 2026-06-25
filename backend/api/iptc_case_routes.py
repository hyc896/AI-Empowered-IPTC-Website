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
from backend.api.knowledge_graph_routes import load_knowledge_points
from backend.database.entities import IPTCCase


router = APIRouter(prefix="/api/v1/iptc", tags=["IPTC案例"])


@router.post("/trigger-matching")
def trigger_matching():
    try:
        from backend.tasks.case_tasks import run_batch_match_cases
        task = run_batch_match_cases.apply_async(queue="default")
        return {"task_id": task.id, "message": "撞库匹配任务已触发"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")


@router.post("/trigger-case-generation")
def trigger_case_generation():
    try:
        from backend.tasks.case_tasks import run_batch_match_cases
        task = run_batch_match_cases.apply_async(queue="default")
        return {"task_id": task.id, "message": "案例生成任务已触发"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")

@router.get("/cases")
def get_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    knowledge_point_name: Optional[str] = Query(None, description="知识点名称过滤"),
    knowledge_point_id: Optional[str] = Query(None, description="知识点ID过滤（已废弃，请用name）"),
    search: Optional[str] = Query(None),
    primary_region: Optional[str] = Query(None),
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
        # 支持按名称或ID过滤（兼容旧版ID格式）
        kp_name = knowledge_point_name
        result = IPTCCaseService.get_cases(
            db=db,
            page=page,
            page_size=page_size,
            knowledge_point_name=kp_name,
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
    try:
        success = IPTCCaseService.delete_case(db, case_id)
        if not success:
            raise HTTPException(status_code=404, detail="案例不存在")
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除案例失败: {str(e)}")


@router.get("/knowledge-tree")
def get_knowledge_tree(db: Session = Depends(get_db_session)):
    """按书→章→节→知识点层级返回，附带每个知识点的真实案例数"""
    try:
        kps = load_knowledge_points()
        # 直接从 iptc_cases 按名称统计
        from sqlalchemy import func, text
        cases_all = db.query(IPTCCase.related_knowledge_points).all()
        name_to_count = {}
        for (kps,) in cases_all:
            if not kps:
                continue
            for kp in kps:
                name = kp.get('name', '') if isinstance(kp, dict) else str(kp)
                if name:
                    name_to_count[name] = name_to_count.get(name, 0) + 1

        # 合并马克思两个book_id为一个
        MARX_IDS = {'marx_principles_2023', 'marx_basic_principles_2023'}
        books = {}
        chapters = {}
        sections = {}

        for idx, kp in enumerate(kps):
            raw_book_id = kp.get('book_id', '')
            book_id = 'marx_basic_principles_2023' if raw_book_id in MARX_IDS else raw_book_id
            book_name = '马克思主义基本原理（2023年版）' if raw_book_id in MARX_IDS else kp.get('book_name', '')

            if book_id not in books:
                books[book_id] = {'book_id': book_id, 'book_name': book_name, 'chapters': {}}

            chap_id = kp.get('chapter_id', '')
            if chap_id and chap_id not in books[book_id]['chapters']:
                books[book_id]['chapters'][chap_id] = {'id': chap_id, 'label': kp.get('chapter', ''), 'sections': {}}

            sec_id = kp.get('section_id', '')
            if chap_id and sec_id and sec_id not in books[book_id]['chapters'].get(chap_id, {}).get('sections', {}):
                books[book_id]['chapters'][chap_id]['sections'][sec_id] = {
                    'id': sec_id, 'label': kp.get('section', ''), 'knowledge_points': []
                }

            kp_name = kp.get('name', '')
            kp_entry = {'id': f'kp_{idx}', 'name': kp_name, 'case_count': name_to_count.get(kp_name, 0)}
            if chap_id and sec_id:
                books[book_id]['chapters'][chap_id]['sections'][sec_id]['knowledge_points'].append(kp_entry)

        result = []
        for b in books.values():
            chapters_list = []
            for ch in b['chapters'].values():
                sections_list = [s for s in ch['sections'].values()]
                chapters_list.append({'id': ch['id'], 'label': ch['label'], 'sections': sections_list})
            result.append({'book_id': b['book_id'], 'book_name': b['book_name'], 'chapters': chapters_list})

        return {'code': 200, 'message': 'success', 'data': result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识点树失败: {str(e)}")
