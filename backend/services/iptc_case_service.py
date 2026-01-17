# -*- coding: utf-8 -*-
"""
思政课案例服务
提供案例查询、检索等功能
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from backend.database.entities import IPTCCase, IPTCKnowledgePointStats, IPTCMessageKnowledgeRelation

logger = logging.getLogger(__name__)


class IPTCCaseService:
    """思政课案例服务"""

    @staticmethod
    def get_cases(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        knowledge_point_id: Optional[str] = None,
        search_keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取案例列表（分页）

        Args:
            db: 数据库会话
            page: 页码（从1开始）
            page_size: 每页数量
            knowledge_point_id: 知识点ID过滤（可选）
            search_keyword: 搜索关键词（标题或内容）

        Returns:
            包含cases列表、total总数、page、page_size的字典
        """
        try:
            query = db.query(IPTCCase)

            # 知识点筛选
            if knowledge_point_id:
                query = query.filter(
                    IPTCCase.related_knowledge_points.contains([{"id": knowledge_point_id}])
                )

            # 关键词搜索
            if search_keyword:
                search_pattern = f"%{search_keyword}%"
                query = query.filter(
                    (IPTCCase.title.like(search_pattern)) |
                    (IPTCCase.content.like(search_pattern)) |
                    (IPTCCase.summary.like(search_pattern))
                )

            # 总数
            total = query.count()

            # 分页查询
            cases = query.order_by(desc(IPTCCase.created_at)).offset(
                (page - 1) * page_size
            ).limit(page_size).all()

            # 转换为前端期望的格式
            items = []
            for case in cases:
                # 提取知识点名称数组
                knowledge_points = []
                if case.related_knowledge_points:
                    for kp in case.related_knowledge_points:
                        if isinstance(kp, dict) and 'name' in kp:
                            knowledge_points.append(kp['name'])

                items.append({
                    "id": case.id,
                    "title": case.title,
                    "content": case.content or "",  # 补充content字段
                    "summary": case.summary or "",
                    "source": "IPTC系统",  # 补充source字段
                    "sourceUrl": case.source_url,  # 驼峰命名
                    "publishDate": case.published_at.isoformat() if case.published_at else case.created_at.isoformat(),  # 驼峰命名
                    "viewCount": 0,  # 补充viewCount字段（暂时为0）
                    "knowledgePoints": knowledge_points,  # 驼峰命名，字符串数组
                    "createdAt": case.created_at.isoformat(),  # 驼峰命名
                    "updatedAt": case.updated_at.isoformat(),  # 驼峰命名
                })

            return {
                "items": items,  # 使用items而不是cases
                "total": total,
                "page": page,
                "pageSize": page_size,  # 驼峰命名
                "totalPages": (total + page_size - 1) // page_size  # 驼峰命名
            }

        except Exception as e:
            logger.error(f"获取案例列表失败: {e}")
            raise

    @staticmethod
    def get_case_by_id(db: Session, case_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个案例详情

        Args:
            db: 数据库会话
            case_id: 案例ID

        Returns:
            案例详情字典，不存在返回None
        """
        try:
            case = db.query(IPTCCase).filter_by(id=case_id).first()

            if not case:
                return None

            # 提取知识点名称数组
            knowledge_points = []
            if case.related_knowledge_points:
                for kp in case.related_knowledge_points:
                    if isinstance(kp, dict) and 'name' in kp:
                        knowledge_points.append(kp['name'])

            return {
                "id": case.id,
                "title": case.title,
                "content": case.content or "",
                "summary": case.summary or "",
                "source": "IPTC系统",
                "sourceUrl": case.source_url,
                "publishDate": case.published_at.isoformat() if case.published_at else case.created_at.isoformat(),
                "viewCount": 0,
                "knowledgePoints": knowledge_points,
                "createdAt": case.created_at.isoformat(),
                "updatedAt": case.updated_at.isoformat(),
                # 保留原始数据供调试
                "tags": case.tags,
                "relatedKnowledgePointsRaw": case.related_knowledge_points,
                "sourceMessageIds": case.source_message_ids,
            }

        except Exception as e:
            logger.error(f"获取案例详情失败: {e}")
            raise

    @staticmethod
    def get_knowledge_points_with_stats(db: Session) -> List[Dict[str, Any]]:
        """
        获取知识点列表及统计信息

        Args:
            db: 数据库会话

        Returns:
            知识点列表
        """
        try:
            # 查询所有知识点统计
            stats = db.query(IPTCKnowledgePointStats).all()

            # 统计每个知识点的案例数
            case_counts = {}
            cases = db.query(IPTCCase).all()
            for case in cases:
                if case.related_knowledge_points:
                    for kp in case.related_knowledge_points:
                        kp_id = kp.get('id')
                        if kp_id:
                            case_counts[kp_id] = case_counts.get(kp_id, 0) + 1

            result = []
            for stat in stats:
                result.append({
                    "id": stat.knowledge_point_id,
                    "name": stat.knowledge_point_name,
                    "matched_message_count": stat.matched_message_count,
                    "case_generated": stat.case_generated == 1,
                    "case_count": case_counts.get(stat.knowledge_point_id, 0),
                    "last_matched_at": stat.last_matched_at.isoformat() if stat.last_matched_at else None,
                })

            return result

        except Exception as e:
            logger.error(f"获取知识点列表失败: {e}")
            raise

    @staticmethod
    def get_statistics(db: Session) -> Dict[str, Any]:
        """
        获取整体统计信息

        Args:
            db: 数据库会话

        Returns:
            统计信息字典
        """
        try:
            # 案例总数
            total_cases = db.query(func.count(IPTCCase.id)).scalar()

            # 知识点总数
            total_kps = db.query(func.count(IPTCKnowledgePointStats.id)).scalar()

            # 已生成案例的知识点数
            generated_kps = db.query(func.count(IPTCKnowledgePointStats.id)).filter(
                IPTCKnowledgePointStats.case_generated == 1
            ).scalar()

            # 消息-知识点关联总数
            total_relations = db.query(func.count(IPTCMessageKnowledgeRelation.id)).scalar()

            # 最近生成的案例
            latest_cases = db.query(IPTCCase).order_by(
                desc(IPTCCase.created_at)
            ).limit(5).all()

            return {
                "total_cases": total_cases,
                "total_knowledge_points": total_kps,
                "generated_knowledge_points": generated_kps,
                "total_relations": total_relations,
                "latest_cases": [
                    {
                        "id": case.id,
                        "title": case.title,
                        "created_at": case.created_at.isoformat(),
                    }
                    for case in latest_cases
                ]
            }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise
