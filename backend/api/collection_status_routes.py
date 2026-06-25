# -*- coding: utf-8 -*-
"""
采集状态API路由
提供消息采集状况的实时数据
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import Dict, Any, List

from backend.database.connection import get_db_session
from backend.database.entities import MessageSource, IPTCKnowledgePointStats, IPTCCase
from backend.database.orm_registry import get_orm_registry

router = APIRouter(prefix="/api/v1/collection", tags=["采集状态"])

# 全局变量：记录任务执行时间
_last_case_generation_time = None
_last_batch_match_time = None


@router.get("/scheduler-info")
def get_scheduler_info(db: Session = Depends(get_db_session)):
    """
    获取调度器信息

    返回：
    - 消息采集任务：每小时执行一次
    - 撞库任务：每12小时执行一次
    - 下次执行时间（基于真实数据计算）
    """
    try:
        now = datetime.now()

        # ========== 消息采集任务：每小时执行 ==========
        collection_interval = 3600  # 1小时 = 3600秒

        # 从数据库获取最近一次消息采集时间
        latest_source = db.query(MessageSource).filter(
            MessageSource.last_crawled_at.isnot(None)
        ).order_by(desc(MessageSource.last_crawled_at)).first()

        if latest_source and latest_source.last_crawled_at:
            # 基于最近采集时间计算下次执行时间
            last_collection_time = latest_source.last_crawled_at
            elapsed = (now - last_collection_time).total_seconds()
            collection_next_in_seconds = max(0, collection_interval - (elapsed % collection_interval))
            collection_last_run_at = last_collection_time.isoformat()
        else:
            # 如果没有采集记录，假设下次在1小时后
            collection_next_in_seconds = collection_interval
            collection_last_run_at = None

        # ========== 撞库任务：每12小时执行 ==========
        batch_match_interval = 43200  # 12小时 = 43200秒

        # 从数据库获取最近一次撞库匹配时间
        latest_match = db.query(IPTCKnowledgePointStats).filter(
            IPTCKnowledgePointStats.last_matched_at.isnot(None)
        ).order_by(desc(IPTCKnowledgePointStats.last_matched_at)).first()

        if latest_match and latest_match.last_matched_at:
            # 基于最近匹配时间计算下次执行时间
            last_match_time = latest_match.last_matched_at
            elapsed = (now - last_match_time).total_seconds()
            batch_next_in_seconds = max(0, batch_match_interval - (elapsed % batch_match_interval))
            batch_last_run_at = last_match_time.isoformat()
        else:
            # 如果没有匹配记录，假设下次在12小时后
            batch_next_in_seconds = batch_match_interval
            batch_last_run_at = None

        return {
            "case_generation": {
                "interval_seconds": collection_interval,
                "interval_text": "每小时",
                "next_run_in_seconds": int(collection_next_in_seconds),
                "last_run_at": collection_last_run_at
            },
            "batch_match": {
                "interval_seconds": batch_match_interval,
                "interval_text": "每12小时",
                "next_run_in_seconds": int(batch_next_in_seconds),
                "last_run_at": batch_last_run_at
            },
            "updated_at": now.isoformat()
        }

    except Exception as e:
        return {
            "error": str(e),
            "case_generation": {
                "interval_seconds": 3600,
                "interval_text": "每小时",
                "next_run_in_seconds": 3600,
                "last_run_at": None
            },
            "batch_match": {
                "interval_seconds": 43200,
                "interval_text": "每12小时",
                "next_run_in_seconds": 43200,
                "last_run_at": None
            }
        }


@router.get("/status")
def get_collection_status(db: Session = Depends(get_db_session)):
    """
    获取采集状态概览

    返回：
    - 消息源总数和激活数
    - 各消息源的消息数量
    - 最近采集时间
    - 中国来源消息总数
    """
    try:
        # 只获取激活的消息源
        sources = db.query(MessageSource).filter(
            MessageSource.is_active == True
        ).all()

        # 获取ORM Registry
        orm_registry = get_orm_registry()

        # 统计各消息源的消息数量（只显示有数据的）
        source_stats = []
        total_messages = 0
        chinese_messages = 0

        for source in sources:
            config = source.config or {}
            table_name = config.get('mysql_table')

            if not table_name:
                continue

            model = orm_registry.get_model(table_name)
            if not model:
                continue

            # 查询消息数量
            count = db.query(func.count(model.id)).scalar() or 0

            # 跳过没有数据的消息源
            if count == 0:
                continue

            total_messages += count

            # 查询最近采集时间
            latest = db.query(model).order_by(desc(model.crawled_at)).first()
            latest_time = latest.crawled_at.isoformat() if latest and hasattr(latest, 'crawled_at') else None

            # 判断是否为中国来源
            is_chinese = _is_chinese_source(source)
            if is_chinese:
                chinese_messages += count

            source_stats.append({
                "name": source.display_name or source.name,
                "source_name": source.name,
                "table": table_name,
                "is_active": source.is_active,
                "is_chinese": is_chinese,
                "message_count": count,
                "latest_crawled_at": latest_time
            })

        # 按消息数量降序排列
        source_stats.sort(key=lambda x: x["message_count"], reverse=True)

        return {
            "total_sources": len(source_stats),
            "active_sources": len(source_stats),
            "total_messages": total_messages,
            "chinese_messages": chinese_messages,
            "sources": source_stats,
            "updated_at": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "error": str(e),
            "total_sources": 0,
            "active_sources": 0,
            "total_messages": 0,
            "chinese_messages": 0,
            "sources": []
        }


@router.get("/matching-status")
def get_matching_status(db: Session = Depends(get_db_session)):
    """
    获取撞库匹配状态

    返回：
    - 知识点总数
    - 已匹配知识点数
    - 已生成案例的知识点数
    - 案例总数
    - 最近生成的案例
    """
    try:
        # 知识点统计
        total_kps = db.query(func.count(IPTCKnowledgePointStats.id)).scalar() or 0

        matched_kps = db.query(func.count(IPTCKnowledgePointStats.id)).filter(
            IPTCKnowledgePointStats.matched_message_count > 0
        ).scalar() or 0

        generated_kps = db.query(func.count(IPTCKnowledgePointStats.id)).filter(
            IPTCKnowledgePointStats.case_generated == 1
        ).scalar() or 0

        # 案例统计
        total_cases = db.query(func.count(IPTCCase.id)).scalar() or 0

        # 最近生成的案例
        recent_cases = db.query(IPTCCase).order_by(
            desc(IPTCCase.created_at)
        ).limit(5).all()

        recent_cases_data = [
            {
                "id": case.id,
                "title": case.title,
                "created_at": case.created_at.isoformat()
            }
            for case in recent_cases
        ]

        # 计算匹配进度
        matching_progress = (matched_kps / total_kps * 100) if total_kps > 0 else 0
        generation_progress = (generated_kps / total_kps * 100) if total_kps > 0 else 0

        return {
            "total_knowledge_points": total_kps,
            "matched_knowledge_points": matched_kps,
            "generated_knowledge_points": generated_kps,
            "total_cases": total_cases,
            "matching_progress": round(matching_progress, 2),
            "generation_progress": round(generation_progress, 2),
            "recent_cases": recent_cases_data,
            "updated_at": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "error": str(e),
            "total_knowledge_points": 0,
            "matched_knowledge_points": 0,
            "generated_knowledge_points": 0,
            "total_cases": 0,
            "matching_progress": 0,
            "generation_progress": 0,
            "recent_cases": []
        }


def _is_chinese_source(source: MessageSource) -> bool:
    """判断是否为中国来源"""
    known_chinese_names = {
        'people_theory', 'gmw_theory', 'cssn', 'qstheory',
        'tonghuashun', 'securities_times', 'kr36',
        '同花顺快讯', '证券时报',
    }

    if source.name in known_chinese_names:
        return True

    config = source.config or {}
    inner_config = config.get('config', {})

    region = inner_config.get('region', '')
    if region and ('中国' in region or 'CN' in region.upper()):
        return True

    language = inner_config.get('language', '')
    if language and language.lower() == 'zh':
        return True

    return False
