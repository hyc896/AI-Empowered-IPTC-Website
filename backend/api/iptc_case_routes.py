# -*- coding: utf-8 -*-
"""
思政课案例API路由
提供案例相关的HTTP接口
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Any, List, Optional

from backend.database.connection import get_db_session
from backend.services.iptc_case_service import IPTCCaseService
from backend.api.knowledge_graph_routes import load_knowledge_points
from backend.database.entities import IPTCCase
from backend.tasks import app as celery_app


router = APIRouter(prefix="/api/v1/iptc", tags=["IPTC案例"])


class PipelineTriggerRequest(BaseModel):
    scope: str = Field("all", description="all/national/shanghai")
    message_ids: Optional[List[str]] = None
    knowledge_point_ids: Optional[List[str]] = None
    case_ids: Optional[List[str]] = None
    limit: Optional[int] = None


def _safe_task_payload(value: Any):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_safe_task_payload(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _safe_task_payload(item) for key, item in value.items()}
    return str(value)


@router.post("/trigger-matching")
def trigger_matching(request: Optional[PipelineTriggerRequest] = None):
    try:
        from backend.tasks.case_tasks import run_matching_only
        request = request or PipelineTriggerRequest()
        task = run_matching_only.apply_async(
            kwargs={
                "scope": request.scope,
                "message_ids": request.message_ids,
            },
            queue="default"
        )
        return {"task_id": task.id, "message": "撞库匹配任务已触发"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")


@router.post("/trigger-case-generation")
def trigger_case_generation(request: Optional[PipelineTriggerRequest] = None):
    try:
        from backend.tasks.case_tasks import run_case_generation_only
        request = request or PipelineTriggerRequest()
        task = run_case_generation_only.apply_async(
            kwargs={
                "scope": request.scope,
                "knowledge_point_ids": request.knowledge_point_ids,
            },
            queue="default"
        )
        return {"task_id": task.id, "message": "案例生成任务已触发"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")


@router.post("/trigger-full-pipeline")
def trigger_full_pipeline(request: Optional[PipelineTriggerRequest] = None):
    try:
        from backend.tasks.case_tasks import run_batch_match_cases
        request = request or PipelineTriggerRequest()
        task = run_batch_match_cases.apply_async(
            kwargs={
                "scope": request.scope,
                "message_ids": request.message_ids,
            },
            queue="default"
        )
        return {"task_id": task.id, "message": "全流程撞库与案例生成任务已触发"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")


@router.post("/trigger-venue-sync")
def trigger_venue_sync(request: Optional[PipelineTriggerRequest] = None):
    try:
        from backend.tasks.case_tasks import run_venue_sync_from_cases
        request = request or PipelineTriggerRequest(scope="shanghai")
        task = run_venue_sync_from_cases.apply_async(
            kwargs={"case_ids": request.case_ids},
            queue="default"
        )
        return {"task_id": task.id, "message": "上海案例实践地点提取任务已触发"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")


@router.get("/tasks/{task_id}")
def get_pipeline_task_status(task_id: str):
    """查询撞库、案例生成、全流程和场馆同步任务状态。"""
    try:
        from celery.result import AsyncResult

        task_result = AsyncResult(task_id, app=celery_app)
        payload = {
            "task_id": task_id,
            "state": task_result.state,
            "ready": task_result.ready(),
            "successful": task_result.successful() if task_result.ready() else False,
            "result": None,
            "info": None,
        }

        if task_result.state == "SUCCESS":
            payload["result"] = _safe_task_payload(task_result.result)
        elif task_result.state == "FAILURE":
            payload["info"] = str(task_result.info)
        elif task_result.state == "RETRY":
            payload["info"] = _safe_task_payload(task_result.info)
        elif task_result.state == "STARTED":
            payload["info"] = "任务执行中"
        elif task_result.state == "PENDING":
            payload["info"] = "任务等待执行"

        return payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询任务状态失败: {str(e)}")


@router.get("/candidates/messages")
def list_message_candidates(
    scope: str = Query("all", pattern="^(all|national|shanghai)$"),
    limit: int = Query(100, ge=1, le=500),
    source_table: Optional[str] = Query(None),
    unprocessed_only: bool = Query(False),
    local_only: Optional[bool] = Query(None),
):
    try:
        from backend.scripts.batch_match_cases import BatchMatchCasesService
        service = BatchMatchCasesService()
        return {
            "code": 200,
            "message": "success",
            "data": service.list_collected_messages(
                scope=scope,
                limit=limit,
                source_table=source_table,
                unprocessed_only=unprocessed_only,
                local_only=local_only,
            )
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取消息候选列表失败: {str(e)}")


@router.get("/candidates/matches")
def list_match_candidates(
    scope: str = Query("all", pattern="^(all|national|shanghai)$"),
    limit: int = Query(200, ge=1, le=1000),
):
    try:
        from backend.scripts.batch_match_cases import BatchMatchCasesService
        service = BatchMatchCasesService()
        return {
            "code": 200,
            "message": "success",
            "data": service.list_match_results(scope=scope, limit=limit)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取匹配列表失败: {str(e)}")


@router.get("/candidates/cases")
def list_case_candidates(
    scope: str = Query("all", pattern="^(all|national|shanghai)$"),
    limit: int = Query(100, ge=1, le=500),
):
    try:
        from backend.scripts.batch_match_cases import BatchMatchCasesService
        service = BatchMatchCasesService()
        return {
            "code": 200,
            "message": "success",
            "data": service.list_case_candidates(scope=scope, limit=limit)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取案例候选列表失败: {str(e)}")

@router.get("/cases")
def get_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    knowledge_point_name: Optional[str] = Query(None, description="知识点名称过滤"),
    knowledge_point_id: Optional[str] = Query(None, description="知识点ID过滤（已废弃，请用name）"),
    search: Optional[str] = Query(None),
    primary_region: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
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
            primary_region=primary_region or scope
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
def get_knowledge_tree(
    primary_region: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
    db: Session = Depends(get_db_session)
):
    """按书→章→节→知识点层级返回，附带每个知识点的真实案例数。"""
    try:
        raw_kps = load_knowledge_points()
        if isinstance(raw_kps, dict):
            raw_kps = raw_kps.get("knowledge_points") or raw_kps.get("data") or raw_kps.get("items") or []

        case_query = db.query(IPTCCase.related_knowledge_points)
        case_query = IPTCCaseService.apply_region_filter(
            case_query,
            IPTCCase.primary_region,
            primary_region,
            scope,
        )

        name_to_count = {}
        id_to_count = {}
        for (case_kps,) in case_query.all():
            if not case_kps:
                continue
            for kp in case_kps:
                if isinstance(kp, dict):
                    kp_id = str(kp.get("id") or "")
                    name = str(kp.get("name") or "")
                    if kp_id:
                        id_to_count[kp_id] = id_to_count.get(kp_id, 0) + 1
                    if name:
                        name_to_count[name] = name_to_count.get(name, 0) + 1
                else:
                    name = str(kp)
                    if name:
                        name_to_count[name] = name_to_count.get(name, 0) + 1

        def text_value(data, *keys, default=""):
            for key in keys:
                value = data.get(key)
                if value not in (None, ""):
                    return str(value)
            return default

        def stable_id(prefix: str, value: str, fallback: int) -> str:
            cleaned = "".join(ch if ch.isalnum() else "_" for ch in value).strip("_")
            return f"{prefix}_{cleaned or fallback}"

        MARX_IDS = {"marx_principles_2023", "marx_basic_principles_2023"}
        books = {}

        for idx, kp in enumerate(raw_kps):
            if not isinstance(kp, dict):
                kp = {"name": str(kp)}

            kp_name = text_value(kp, "name", "knowledge_point_name", "title")
            if not kp_name:
                continue

            raw_book_id = text_value(kp, "book_id")
            raw_book_name = text_value(kp, "book_name", "book", default="思政知识点")
            if raw_book_id in MARX_IDS:
                book_id = "marx_basic_principles_2023"
                book_name = "马克思主义基本原理（2023年版）"
            else:
                book_name = raw_book_name
                book_id = raw_book_id or stable_id("book", book_name, 1)

            chapter_label = text_value(kp, "chapter", "chapter_name", "chapter_title", default="全部知识点")
            chapter_id = text_value(kp, "chapter_id") or stable_id(f"{book_id}_chapter", chapter_label, idx)

            section_label = text_value(kp, "section", "section_name", "section_title", "part", default="未分组知识点")
            section_id = text_value(kp, "section_id") or stable_id(f"{chapter_id}_section", section_label, idx)

            kp_id = text_value(kp, "id", "knowledge_point_id", "point_id") or f"kp_{idx}"
            case_count = id_to_count.get(kp_id, name_to_count.get(kp_name, 0))

            if book_id not in books:
                books[book_id] = {"book_id": book_id, "book_name": book_name, "chapters": {}}

            book = books[book_id]
            if chapter_id not in book["chapters"]:
                book["chapters"][chapter_id] = {"id": chapter_id, "label": chapter_label, "sections": {}}

            chapter = book["chapters"][chapter_id]
            if section_id not in chapter["sections"]:
                chapter["sections"][section_id] = {
                    "id": section_id,
                    "label": section_label,
                    "knowledge_points": [],
                    "case_count": 0,
                }

            section = chapter["sections"][section_id]
            section["knowledge_points"].append({
                "id": kp_id,
                "name": kp_name,
                "case_count": case_count,
            })
            section["case_count"] += case_count

        result = []
        for b in books.values():
            chapters_list = []
            for ch in b["chapters"].values():
                sections_list = list(ch["sections"].values())
                chapter_count = sum(s.get("case_count", 0) for s in sections_list)
                chapters_list.append({
                    "id": ch["id"],
                    "label": ch["label"],
                    "case_count": chapter_count,
                    "sections": sections_list,
                })
            result.append({
                "book_id": b["book_id"],
                "book_name": b["book_name"],
                "case_count": sum(ch.get("case_count", 0) for ch in chapters_list),
                "chapters": chapters_list,
            })

        return {"code": 200, "message": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识点树失败: {str(e)}")
