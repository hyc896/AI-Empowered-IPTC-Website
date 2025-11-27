# -*- coding: utf-8 -*-

"""
AI Report Celery Tasks
AI日报Celery任务定义
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, date

from backend.tasks import app, run_async_task
from backend.services.ai_report_generator import AIReportGenerator

logger = logging.getLogger(__name__)


@app.task(
    name='backend.tasks.ai_report_tasks.generate_daily_report',
    bind=True,
    max_retries=1,
    default_retry_delay=600,  # 失败后10分钟重试
    time_limit=1800,  # 30分钟硬限制
    soft_time_limit=1650  # 27.5分钟软限制
)
def generate_daily_report(self, report_type: str, report_date: Optional[str] = None) -> Dict[str, Any]:
    """
    生成AI日报（通用任务）

    Args:
        report_type: 报告类型（governance/research/industry/comprehensive）
        report_date: 报告日期（YYYY-MM-DD），None表示今天

    Returns:
        生成结果字典: {
            'success': bool,
            'report_type': str,
            'report_date': str,
            'report_id': str | None,
            'duration_seconds': float,
            'error': str | None
        }

    Raises:
        Retry: 生成失败时自动重试
    """
    start_time = datetime.now()
    logger.info(f"【Celery日报】开始生成: {report_type}, 日期: {report_date or '今天'}")

    try:
        # 1. 解析日期
        target_date = None
        if report_date:
            try:
                target_date = datetime.strptime(report_date, '%Y-%m-%d')
            except ValueError as e:
                error_msg = f"日期格式错误: {report_date}, 应为YYYY-MM-DD"
                logger.error(f"【Celery日报】{error_msg}")
                return {
                    'success': False,
                    'report_type': report_type,
                    'report_date': report_date,
                    'report_id': None,
                    'duration_seconds': 0,
                    'error': error_msg
                }

        # 2. 创建报告生成器
        generator = AIReportGenerator()

        # 3. 根据报告类型调用对应的生成方法
        async def generate_report():
            if report_type == 'governance':
                return await generator.generate_governance_report(target_date)
            elif report_type == 'research':
                return await generator.generate_research_report(target_date)
            elif report_type == 'industry':
                return await generator.generate_industry_report(target_date)
            elif report_type == 'comprehensive':
                return await generator.generate_daily_report(target_date, report_type='comprehensive')
            elif report_type == 'china_ai':
                return await generator.generate_china_ai_report(target_date)
            elif report_type == 'shanghai_weekly':
                return await generator.generate_shanghai_weekly_report(target_date)
            else:
                raise ValueError(f"未知的报告类型: {report_type}")

        report_id = run_async_task(generate_report())

        # 4. 返回结果
        duration_seconds = (datetime.now() - start_time).total_seconds()

        if report_id:
            logger.info(
                f"【Celery日报】✓ 生成成功: {report_type} "
                f"(ID: {report_id}, 耗时: {duration_seconds:.2f}s)"
            )
            return {
                'success': True,
                'report_type': report_type,
                'report_date': report_date or datetime.now().strftime('%Y-%m-%d'),
                'report_id': report_id,
                'duration_seconds': duration_seconds,
                'error': None
            }
        else:
            error_msg = f"报告生成返回空ID"
            logger.error(f"【Celery日报】{error_msg}: {report_type}")
            return {
                'success': False,
                'report_type': report_type,
                'report_date': report_date or datetime.now().strftime('%Y-%m-%d'),
                'report_id': None,
                'duration_seconds': duration_seconds,
                'error': error_msg
            }

    except Exception as e:
        duration_seconds = (datetime.now() - start_time).total_seconds()
        logger.error(f"【Celery日报】❌ 生成失败: {report_type}, 错误: {e}", exc_info=True)

        # 重试逻辑
        if self.request.retries < self.max_retries:
            logger.warning(f"【Celery日报】重试中: {report_type} ({self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e)

        return {
            'success': False,
            'report_type': report_type,
            'report_date': report_date or datetime.now().strftime('%Y-%m-%d'),
            'report_id': None,
            'duration_seconds': duration_seconds,
            'error': str(e)
        }


# ========================
# 便捷任务（为每种报告类型创建专用任务）
# ========================

@app.task(
    name='backend.tasks.ai_report_tasks.generate_governance_report',
    time_limit=1800,
    soft_time_limit=1650
)
def generate_governance_report_task(report_date: Optional[str] = None) -> Dict[str, Any]:
    """
    生成AI治理日报

    Args:
        report_date: 报告日期（YYYY-MM-DD）

    Returns:
        生成结果字典
    """
    return generate_daily_report.apply(kwargs={
        'report_type': 'governance',
        'report_date': report_date
    }).get()


@app.task(
    name='backend.tasks.ai_report_tasks.generate_research_report',
    time_limit=1800,
    soft_time_limit=1650
)
def generate_research_report_task(report_date: Optional[str] = None) -> Dict[str, Any]:
    """
    生成AI科技日报

    Args:
        report_date: 报告日期（YYYY-MM-DD）

    Returns:
        生成结果字典
    """
    return generate_daily_report.apply(kwargs={
        'report_type': 'research',
        'report_date': report_date
    }).get()


@app.task(
    name='backend.tasks.ai_report_tasks.generate_industry_report',
    time_limit=1800,
    soft_time_limit=1650
)
def generate_industry_report_task(report_date: Optional[str] = None) -> Dict[str, Any]:
    """
    生成AI产业日报

    Args:
        report_date: 报告日期（YYYY-MM-DD）

    Returns:
        生成结果字典
    """
    return generate_daily_report.apply(kwargs={
        'report_type': 'industry',
        'report_date': report_date
    }).get()


@app.task(
    name='backend.tasks.ai_report_tasks.generate_china_ai_report',
    time_limit=1800,
    soft_time_limit=1650
)
def generate_china_ai_report_task(report_date: Optional[str] = None) -> Dict[str, Any]:
    """
    生成中国AI日报

    Args:
        report_date: 报告日期（YYYY-MM-DD）

    Returns:
        生成结果字典
    """
    return generate_daily_report.apply(kwargs={
        'report_type': 'china_ai',
        'report_date': report_date
    }).get()


@app.task(
    name='backend.tasks.ai_report_tasks.generate_shanghai_weekly_report',
    time_limit=2400,
    soft_time_limit=2200
)
def generate_shanghai_weekly_report_task(report_date: Optional[str] = None) -> Dict[str, Any]:
    """
    生成上海周报

    Args:
        report_date: 报告日期（YYYY-MM-DD）

    Returns:
        生成结果字典
    """
    return generate_daily_report.apply(kwargs={
        'report_type': 'shanghai_weekly',
        'report_date': report_date
    }).get()
