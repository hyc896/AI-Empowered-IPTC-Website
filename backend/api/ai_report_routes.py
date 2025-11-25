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
async def get_latest_report(
    report_type: str = Query('comprehensive', description="报告类型（comprehensive/governance/research/industry）")
):
    """
    获取最新的AI日报

    Args:
        report_type: 报告类型，默认为comprehensive

    Returns:
        最近生成的指定类型日报
    """
    try:
        with create_session() as db:
            # 查询最新的已完成报告（指定类型）
            report = db.query(AIDailyReport).filter(
                AIDailyReport.generation_status == 'completed',
                AIDailyReport.report_type == report_type
            ).order_by(
                AIDailyReport.report_date.desc()
            ).first()

            if not report:
                report_type_names = {
                    'comprehensive': '综合日报',
                    'governance': '治理日报',
                    'research': '科研日报',
                    'industry': '产业日报'
                }
                report_name = report_type_names.get(report_type, report_type)
                raise HTTPException(
                    status_code=404,
                    detail=f"暂无可用的{report_name}"
                )

            # 转换为响应格式
            return AIDailyReportResponse(
                id=report.id,
                report_date=report.report_date.strftime('%Y-%m-%d'),
                report_type=report.report_type,
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
async def get_report_by_date(
    report_date: str,
    report_type: str = Query('comprehensive', description="报告类型（comprehensive/governance/research/industry）")
):
    """
    根据日期获取AI日报

    Args:
        report_date: 报告日期（YYYY-MM-DD格式）
        report_type: 报告类型，默认为comprehensive

    Returns:
        指定日期和类型的AI日报
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
                AIDailyReport.report_date == parsed_date,
                AIDailyReport.report_type == report_type
            ).first()

            if not report:
                report_type_names = {
                    'comprehensive': '综合日报',
                    'governance': '治理日报',
                    'research': '科研日报',
                    'industry': '产业日报'
                }
                report_name = report_type_names.get(report_type, report_type)
                raise HTTPException(
                    status_code=404,
                    detail=f"{report_date}的{report_name}不存在"
                )

            return AIDailyReportResponse(
                id=report.id,
                report_date=report.report_date.strftime('%Y-%m-%d'),
                report_type=report.report_type,
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
    status: Optional[str] = Query(None, description="生成状态过滤（pending/completed/failed）"),
    report_type: Optional[str] = Query(None, description="报告类型过滤（comprehensive/governance/research/industry）")
):
    """
    获取AI日报列表

    支持分页、状态过滤和类型过滤
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

            # 类型过滤
            if report_type:
                if report_type not in ['comprehensive', 'governance', 'research', 'industry']:
                    raise HTTPException(
                        status_code=400,
                        detail="类型参数错误，应为comprehensive/governance/research/industry之一"
                    )
                query = query.filter(AIDailyReport.report_type == report_type)

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
                    report_type=report.report_type,
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
async def trigger_report_generation(
    report_type: str = Query('governance', description="报告类型（governance/research/industry）"),
    report_date: Optional[str] = Query(None, description="报告日期（YYYY-MM-DD格式），默认为今天")
):
    """
    手动触发AI日报生成

    Args:
        report_type: 报告类型，默认为comprehensive
        report_date: 报告日期，默认为今天

    用于测试或补充生成，任务在后台异步执行

    Returns:
        任务提交确认信息
    """
    try:
        # 验证report_type
        if report_type not in ['comprehensive', 'governance', 'research', 'industry']:
            raise HTTPException(
                status_code=400,
                detail="类型参数错误，应为comprehensive/governance/research/industry之一"
            )

        # 解析日期
        target_date = None
        if report_date:
            try:
                target_date = datetime.strptime(report_date, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="日期格式错误，应为YYYY-MM-DD格式"
                )

        from ..services.ai_report_generator import get_report_generator

        report_type_names = {
            'comprehensive': '综合日报',
            'governance': '治理日报',
            'research': '科研日报',
            'industry': '产业日报'
        }
        report_name = report_type_names.get(report_type, report_type)

        # 导入Celery任务并提交到队列
        from backend.tasks.ai_report_tasks import generate_daily_report as celery_generate_report

        task = celery_generate_report.apply_async(
            kwargs={
                'report_type': report_type if report_type != 'comprehensive' else 'governance',
                'report_date': report_date
            },
            queue='report',
            priority=9  # 高优先级
        )

        date_info = f"（{report_date}）" if report_date else "（今天）"
        logger.info(f"【AI日报】手动生成任务已提交：{report_name}{date_info}, task_id: {task.id}")

        return {
            "message": f"{report_name}生成任务已提交{date_info}，正在后台执行",
            "report_type": report_type,
            "report_date": report_date or datetime.now().date().isoformat(),
            "task_id": task.id,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"触发AI日报生成失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"触发AI日报生成失败: {str(e)}"
        )
