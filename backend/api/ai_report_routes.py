# -*- coding: utf-8 -*-

"""
AI日报API路由
提供AI日报的查询和生成功能
"""

import logging
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from ..database.connection import create_session
from ..database.entities import AIDailyReport
from ..api.schemas import AIDailyReportResponse, AIDailyReportListResponse
from ..services.scheduler_service import get_scheduler_service

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/ai-reports",
    tags=["AI日报"]
)


@router.get("/latest", response_model=AIDailyReportResponse)
async def get_latest_report():
    """
    获取最新的AI日报

    返回最近生成的一份日报
    """
    try:
        with create_session() as db:
            # 查询最新的已完成报告
            report = db.query(AIDailyReport).filter(
                AIDailyReport.generation_status == 'completed'
            ).order_by(
                AIDailyReport.report_date.desc()
            ).first()

            if not report:
                raise HTTPException(
                    status_code=404,
                    detail="暂无可用的AI日报"
                )

            # 转换为响应格式
            return AIDailyReportResponse(
                id=report.id,
                report_date=report.report_date.strftime('%Y-%m-%d'),
                content=report.content,
                statistics=report.statistics,
                governance_count=report.governance_count,
                research_count=report.research_count,
                industry_count=report.industry_count,
                total_messages=report.total_messages,
                generation_status=report.generation_status,
                error_message=report.error_message,
                generated_at=report.generated_at,
                model_version=report.model_version
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取最新AI日报失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取最新AI日报失败: {str(e)}"
        )


@router.get("/{report_date}", response_model=AIDailyReportResponse)
async def get_report_by_date(report_date: str):
    """
    根据日期获取AI日报

    Args:
        report_date: 报告日期（YYYY-MM-DD格式）

    Returns:
        指定日期的AI日报
    """
    try:
        # 解析日期
        try:
            parsed_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="日期格式错误，应为YYYY-MM-DD格式"
            )

        with create_session() as db:
            report = db.query(AIDailyReport).filter(
                AIDailyReport.report_date == parsed_date
            ).first()

            if not report:
                raise HTTPException(
                    status_code=404,
                    detail=f"{report_date}的AI日报不存在"
                )

            return AIDailyReportResponse(
                id=report.id,
                report_date=report.report_date.strftime('%Y-%m-%d'),
                content=report.content,
                statistics=report.statistics,
                governance_count=report.governance_count,
                research_count=report.research_count,
                industry_count=report.industry_count,
                total_messages=report.total_messages,
                generation_status=report.generation_status,
                error_message=report.error_message,
                generated_at=report.generated_at,
                model_version=report.model_version
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取AI日报失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取AI日报失败: {str(e)}"
        )


@router.get("", response_model=AIDailyReportListResponse)
async def list_reports(
    limit: int = Query(10, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    status: Optional[str] = Query(None, description="生成状态过滤（pending/completed/failed）")
):
    """
    获取AI日报列表

    支持分页和状态过滤
    """
    try:
        with create_session() as db:
            # 构建查询
            query = db.query(AIDailyReport)

            # 状态过滤
            if status:
                if status not in ['pending', 'completed', 'failed']:
                    raise HTTPException(
                        status_code=400,
                        detail="状态参数错误，应为pending/completed/failed之一"
                    )
                query = query.filter(AIDailyReport.generation_status == status)

            # 获取总数
            total = query.count()

            # 分页查询
            reports = query.order_by(
                AIDailyReport.report_date.desc()
            ).limit(limit).offset(offset).all()

            # 转换为响应格式
            items = [
                AIDailyReportResponse(
                    id=report.id,
                    report_date=report.report_date.strftime('%Y-%m-%d'),
                    content=report.content,
                    statistics=report.statistics,
                    governance_count=report.governance_count,
                    research_count=report.research_count,
                    industry_count=report.industry_count,
                    total_messages=report.total_messages,
                    generation_status=report.generation_status,
                    error_message=report.error_message,
                    generated_at=report.generated_at,
                    model_version=report.model_version
                )
                for report in reports
            ]

            return AIDailyReportListResponse(
                items=items,
                total=total,
                limit=limit,
                offset=offset
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取AI日报列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取AI日报列表失败: {str(e)}"
        )


@router.post("/generate", response_model=dict)
async def trigger_report_generation(background_tasks: BackgroundTasks):
    """
    手动触发AI日报生成

    用于测试或补充生成，任务在后台异步执行

    Returns:
        任务提交确认信息
    """
    try:
        scheduler = get_scheduler_service()

        # 在后台任务中执行生成
        background_tasks.add_task(scheduler.trigger_daily_report_now)

        logger.info("【AI日报】手动生成任务已提交")

        return {
            "message": "AI日报生成任务已提交，正在后台执行",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"触发AI日报生成失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"触发AI日报生成失败: {str(e)}"
        )
