# -*- coding: utf-8 -*-

"""
地理统计API路由
提供按地区聚合的消息统计和查询功能
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import func

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from ..database.connection import create_session
from ..database.entities import MessageSource
from ..database.orm_registry import get_orm_registry
from ..api.schemas import GeoStatisticsResponse, RegionMessagesResponse

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/messages",
    tags=["地理统计"]
)


@router.get("/statistics/by-region", response_model=GeoStatisticsResponse)
async def get_geo_statistics(
    source_id: Optional[str] = Query(None, description="消息源ID"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    industry_tags: Optional[str] = Query(None, description="行业标签，逗号分隔")
):
    """
    获取地理统计数据（按国家聚合）

    功能：
    - 统计各国家的新闻数量
    - 支持按消息源、时间范围、行业标签筛选
    - 返回中文国家名作为key

    返回示例：
    {
      "statistics": {
        "中国": 256,
        "美国": 389,
        "英国": 145
      },
      "total_messages": 790,
      "total_countries": 3,
      "filters_applied": {...}
    }
    """
    try:
        with create_session() as db:
            # 1. 获取消息源列表
            query = db.query(MessageSource).filter(MessageSource.is_active == True)
            if source_id:
                query = query.filter(MessageSource.id == source_id)
            sources = query.all()

            if not sources:
                return GeoStatisticsResponse(
                    statistics={},
                    total_messages=0,
                    total_countries=0,
                    filters_applied={
                        "source_id": source_id,
                        "start_date": start_date,
                        "end_date": end_date,
                        "industry_tags": industry_tags
                    }
                )

            # 2. 动态聚合所有表
            country_counts = {}
            registry = get_orm_registry()

            # 解析行业标签（用于OR条件匹配）
            tag_filters = []
            if industry_tags:
                tags = [tag.strip() for tag in industry_tags.split(',') if tag.strip()]
                tag_filters = tags

            for source in sources:
                table_name = source.config.get('mysql_table') if source.config else None

                if not table_name:
                    logger.warning(f"消息源 {source.name} 缺少mysql_table配置")
                    continue

                model = registry.get_model(table_name)

                if not model:
                    logger.warning(f"消息源 {source.name} 的ORM模型 {table_name} 未找到")
                    continue

                try:
                    # 检查模型是否有region字段（旧表如ArxivMessage可能没有）
                    if not hasattr(model, 'region'):
                        logger.debug(f"表 {table_name} 没有region字段，跳过地理统计")
                        continue

                    # 构建查询：提取region第一级（国家名）
                    subquery = db.query(
                        func.substring_index(model.region, '/', 1).label('country'),
                        func.count().label('count')
                    ).filter(
                        model.region.isnot(None),
                        model.region != ''
                    )

                    # 应用日期筛选
                    if start_date:
                        subquery = subquery.filter(model.published_at >= start_date)
                    if end_date:
                        # 结束日期包含当天，所以加1天
                        from datetime import timedelta
                        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                        subquery = subquery.filter(model.published_at < end_dt)

                    # 应用行业标签筛选（OR逻辑）
                    if tag_filters:
                        tag_conditions = []
                        for tag in tag_filters:
                            tag_conditions.append(model.industry_tags.like(f'%{tag}%'))

                        from sqlalchemy import or_
                        subquery = subquery.filter(or_(*tag_conditions))

                    # 分组统计
                    results = subquery.group_by('country').all()

                    # 累加到country_counts
                    for country, count in results:
                        if country:  # 确保国家名不为空
                            country = country.strip()
                            country_counts[country] = country_counts.get(country, 0) + count

                except Exception as e:
                    logger.error(f"查询表 {table_name} 失败: {e}", exc_info=True)
                    continue

            # 3. 构建响应
            response = GeoStatisticsResponse(
                statistics=country_counts,
                total_messages=sum(country_counts.values()),
                total_countries=len(country_counts),
                filters_applied={
                    "source_id": source_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "industry_tags": industry_tags
                }
            )

            logger.info(f"地理统计完成: {response.total_countries}个国家, {response.total_messages}条消息")

            return response

    except Exception as e:
        logger.error(f"地理统计查询失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"地理统计查询失败: {str(e)}"
        )


@router.get("/by-region/{region_name}", response_model=RegionMessagesResponse)
async def get_messages_by_region(
    region_name: str,
    source_id: Optional[str] = Query(None, description="消息源ID"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    industry_tags: Optional[str] = Query(None, description="行业标签，逗号分隔"),
    limit: int = Query(50, le=100, ge=1, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    获取指定地区的消息列表

    功能：
    - 查询指定国家/地区的所有新闻
    - 支持按消息源、时间范围、行业标签筛选
    - 按发布时间倒序排序
    - 分页返回

    参数：
    - region_name: 地区名（中文），如"中国"、"美国"

    返回：
    - 每条消息包含完整信息：标题、内容、消息源、链接
    """
    try:
        with create_session() as db:
            # 1. 获取消息源列表
            query = db.query(MessageSource).filter(MessageSource.is_active == True)
            if source_id:
                query = query.filter(MessageSource.id == source_id)
            sources = query.all()

            if not sources:
                return RegionMessagesResponse(
                    items=[],
                    total=0,
                    limit=limit,
                    offset=offset,
                    region=region_name
                )

            # 2. 解析行业标签
            tag_filters = []
            if industry_tags:
                tags = [tag.strip() for tag in industry_tags.split(',') if tag.strip()]
                tag_filters = tags

            # 3. 跨表查询消息
            all_messages = []
            registry = get_orm_registry()

            for source in sources:
                table_name = source.config.get('mysql_table') if source.config else None

                if not table_name:
                    continue

                model = registry.get_model(table_name)

                if not model:
                    continue

                try:
                    # 查询该表中region匹配的消息
                    # 使用LIKE匹配：region_name开头（如"中国"匹配"中国/广东省/深圳市"）
                    msg_query = db.query(model).filter(
                        model.region.like(f'{region_name}%')
                    )

                    # 应用日期筛选
                    if start_date:
                        msg_query = msg_query.filter(model.published_at >= start_date)
                    if end_date:
                        from datetime import timedelta
                        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                        msg_query = msg_query.filter(model.published_at < end_dt)

                    # 应用行业标签筛选
                    if tag_filters:
                        tag_conditions = []
                        for tag in tag_filters:
                            tag_conditions.append(model.industry_tags.like(f'%{tag}%'))

                        from sqlalchemy import or_
                        msg_query = msg_query.filter(or_(*tag_conditions))

                    # 执行查询
                    messages = msg_query.all()

                    # 转换为字典格式并添加source_name
                    for msg in messages:
                        # 获取url字段（不同表可能字段名不同）
                        url = getattr(msg, 'url', None) or getattr(msg, 'source_url', None)

                        all_messages.append({
                            "id": msg.id,
                            "title": msg.title,
                            "content": msg.content,
                            "summary": msg.summary or (msg.content[:200] + '...' if msg.content and len(msg.content) > 200 else msg.content),
                            "source_name": source.display_name or source.name,
                            "source_id": msg.source_id,
                            "published_at": msg.published_at.isoformat() if msg.published_at else None,
                            "url": url,
                            "region": msg.region,
                            "industry_tags": msg.industry_tags
                        })

                except Exception as e:
                    logger.error(f"查询表 {table_name} 的地区消息失败: {e}", exc_info=True)
                    continue

            # 4. 排序（按发布时间倒序）
            all_messages.sort(
                key=lambda x: x['published_at'] or '',
                reverse=True
            )

            # 5. 分页
            total = len(all_messages)
            paginated = all_messages[offset:offset+limit]

            logger.info(f"地区 {region_name} 消息查询完成: {total}条, 返回 {len(paginated)}条")

            return RegionMessagesResponse(
                items=paginated,
                total=total,
                limit=limit,
                offset=offset,
                region=region_name
            )

    except Exception as e:
        logger.error(f"地区消息查询失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"地区消息查询失败: {str(e)}"
        )


@router.get("/industry-tags")
async def get_all_industry_tags():
    """
    获取所有可用的行业标签

    功能：
    - 从所有消息表中提取不重复的行业标签
    - 用于前端筛选器的选项列表

    返回：标签数组，如 ["人工智能", "半导体", "新能源", ...]
    """
    try:
        # 预定义的标准行业标签列表
        # 可以从数据库动态提取，但为了性能，这里先用预定义列表
        standard_tags = [
            "人工智能",
            "半导体",
            "芯片",
            "新能源",
            "生物医药",
            "互联网",
            "金融",
            "房地产",
            "制造业",
            "教育",
            "医疗",
            "环保",
            "农业",
            "零售",
            "物流",
            "文娱",
            "游戏",
            "电商",
            "汽车",
            "航空航天",
            "通信",
            "软件",
            "硬件",
            "云计算",
            "大数据",
            "区块链",
            "量子计算",
            "机器人"
        ]

        logger.info(f"返回 {len(standard_tags)} 个行业标签")

        return {
            "tags": standard_tags,
            "total": len(standard_tags)
        }

    except Exception as e:
        logger.error(f"获取行业标签失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取行业标签失败: {str(e)}"
        )
