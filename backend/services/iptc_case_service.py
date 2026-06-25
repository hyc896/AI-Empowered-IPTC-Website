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
import jieba
from rank_bm25 import BM25Okapi

from backend.database.entities import IPTCCase, IPTCKnowledgePointStats, IPTCMessageKnowledgeRelation
from backend.database.orm_registry import get_orm_registry
from backend.storage import get_chromadb_storage

logger = logging.getLogger(__name__)


class IPTCCaseService:
    """思政课案例服务"""

    REGION_ALIASES = {
        "全国": ["全国", "å…¨å›½", "鍏ㄥ浗", "national", "china"],
        "上海": ["上海", "ä¸Šæµ·", "涓婃捣", "shanghai"],
    }

    @staticmethod
    def normalize_region(primary_region: Optional[str] = None, scope: Optional[str] = None) -> Optional[str]:
        """Normalize public region/scope inputs to the stored case region labels."""
        value = (primary_region or scope or "").strip()
        if not value or value in {"all", "全部"}:
            return None
        mapping = {
            "national": "全国",
            "china": "全国",
            "全国": "全国",
            "shanghai": "上海",
            "上海": "上海",
        }
        return mapping.get(value, value)

    @staticmethod
    def region_filter_values(primary_region: Optional[str] = None, scope: Optional[str] = None) -> List[str]:
        normalized = IPTCCaseService.normalize_region(primary_region, scope)
        if not normalized:
            return []
        return IPTCCaseService.REGION_ALIASES.get(normalized, [normalized])

    @staticmethod
    def apply_region_filter(query, column, primary_region: Optional[str] = None, scope: Optional[str] = None):
        values = IPTCCaseService.region_filter_values(primary_region, scope)
        if not values:
            return query
        return query.filter(column.in_(values))

    @staticmethod
    def _case_has_knowledge_point(
        case: IPTCCase,
        knowledge_point_name: Optional[str] = None,
        knowledge_point_id: Optional[str] = None
    ) -> bool:
        if not knowledge_point_name and not knowledge_point_id:
            return True
        for kp in case.related_knowledge_points or []:
            if isinstance(kp, dict):
                if knowledge_point_name and kp.get("name") == knowledge_point_name:
                    return True
                if knowledge_point_id and kp.get("id") == knowledge_point_id:
                    return True
            elif knowledge_point_name and str(kp) == knowledge_point_name:
                return True
        return False

    @staticmethod
    def _tokenize_text(text: str) -> List[str]:
        """
        对文本进行中文分词

        Args:
            text: 待分词的文本

        Returns:
            分词后的词语列表
        """
        if not text:
            return []
        return list(jieba.cut(text.lower()))

    @staticmethod
    def _build_case_corpus(case: IPTCCase) -> str:
        """
        构建案例的搜索语料（标题 + 内容 + 知识点）

        Args:
            case: 案例对象

        Returns:
            合并后的文本
        """
        corpus_parts = [case.title]

        # 添加内容（限制长度以提高性能）
        if case.content:
            # 只取前800字进行分词，避免对超长内容分词导致性能问题
            corpus_parts.append(case.content[:800])

        # 添加摘要（如果存在）
        if case.summary:
            corpus_parts.append(case.summary)

        # 添加知识点名称
        if case.related_knowledge_points:
            for kp in case.related_knowledge_points:
                if isinstance(kp, dict) and 'name' in kp:
                    corpus_parts.append(kp['name'])

        return " ".join(corpus_parts)

    @staticmethod
    def _get_source_messages(db: Session, message_ids: List[str]) -> List[Dict[str, Any]]:
        """
        获取消息的详细信息（标题和URL）

        Args:
            db: 数据库会话
            message_ids: 消息ID列表

        Returns:
            消息信息列表 [{"title": "...", "url": "...", "source_table": "..."}]
        """
        if not message_ids:
            return []

        registry = get_orm_registry()
        messages = []

        for msg_id in message_ids:
            try:
                # 查询消息-知识点关联表，获取source_table
                relation = db.query(IPTCMessageKnowledgeRelation).filter(
                    IPTCMessageKnowledgeRelation.message_id == msg_id
                ).first()

                if not relation:
                    logger.warning(f"未找到消息ID {msg_id} 的关联记录")
                    continue

                # 使用ORM Registry获取对应的模型类
                model = registry.get_model(relation.source_table)

                if not model:
                    logger.warning(f"未找到表模型: {relation.source_table}")
                    continue

                # 查询具体的消息表
                msg = db.query(model).filter(model.id == msg_id).first()

                if msg:
                    messages.append({
                        "title": msg.title,
                        "url": msg.url if hasattr(msg, 'url') else None,
                        "source_table": relation.source_table,
                        "published_at": msg.published_at.isoformat() if hasattr(msg, 'published_at') and msg.published_at else None
                    })
                else:
                    logger.warning(f"未找到消息ID: {msg_id}")

            except Exception as e:
                logger.error(f"获取消息 {msg_id} 详情失败: {e}")
                continue

        return messages

    @staticmethod
    def get_cases(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        knowledge_point_id: Optional[str] = None,
        knowledge_point_name: Optional[str] = None,
        search_keyword: Optional[str] = None,
        primary_region: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            query = db.query(IPTCCase)

            # 地域筛选
            query = IPTCCaseService.apply_region_filter(query, IPTCCase.primary_region, primary_region)

            # 查询所有匹配的案例
            all_cases = query.order_by(desc(IPTCCase.created_at)).all()

            if knowledge_point_name or knowledge_point_id:
                all_cases = [
                    case for case in all_cases
                    if IPTCCaseService._case_has_knowledge_point(
                        case,
                        knowledge_point_name=knowledge_point_name,
                        knowledge_point_id=knowledge_point_id
                    )
                ]

            # 关键词搜索（使用BM25算法）
            if search_keyword and all_cases:
                logger.info(f"使用BM25算法搜索关键词: {search_keyword}")

                # 构建语料库和分词
                corpus_texts = []
                for case in all_cases:
                    corpus_text = IPTCCaseService._build_case_corpus(case)
                    corpus_texts.append(corpus_text)

                # 对语料库进行分词
                tokenized_corpus = [IPTCCaseService._tokenize_text(text) for text in corpus_texts]

                # 对查询关键词进行分词
                tokenized_query = IPTCCaseService._tokenize_text(search_keyword)

                # 创建BM25模型
                bm25 = BM25Okapi(tokenized_corpus)

                # 计算每个案例的BM25分数
                scores = bm25.get_scores(tokenized_query)

                # 将案例和分数配对，并按分数排序
                case_score_pairs = list(zip(all_cases, scores))

                # 设置最低分数阈值（过滤掉低相关性结果）
                # BM25分数通常在0-10之间，3.0可以过滤掉更多低相关性结果，提高搜索质量
                MIN_BM25_SCORE = 3.0

                # 过滤掉分数低于阈值的案例
                case_score_pairs = [(case, score) for case, score in case_score_pairs if score >= MIN_BM25_SCORE]

                # 按BM25分数降序排序
                case_score_pairs.sort(key=lambda x: x[1], reverse=True)

                # 提取排序后的案例
                all_cases = [case for case, score in case_score_pairs]

                logger.info(f"BM25搜索完成，找到 {len(all_cases)} 个相关案例（阈值: {MIN_BM25_SCORE}）")

                # 记录前5个案例的分数（用于调试）
                for i, (case, score) in enumerate(case_score_pairs[:5]):
                    logger.info(f"案例 #{i+1}: {case.title[:30]}... (BM25分数: {score:.4f})")

            # 总数
            total = len(all_cases)

            # 分页
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            cases = all_cases[start_idx:end_idx]

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
                    "source_url": case.source_url,
                    "publishDate": case.published_at.isoformat() if case.published_at else case.created_at.isoformat(),  # 驼峰命名
                    "published_at": case.published_at.isoformat() if case.published_at else None,
                    "viewCount": 0,  # 补充viewCount字段（暂时为0）
                    "knowledgePoints": knowledge_points,  # 驼峰命名，字符串数组
                    "related_knowledge_points": case.related_knowledge_points or [],
                    "primary_region": case.primary_region or "全国",
                    "createdAt": case.created_at.isoformat(),  # 驼峰命名
                    "created_at": case.created_at.isoformat(),
                    "updatedAt": case.updated_at.isoformat(),  # 驼峰命名
                    "updated_at": case.updated_at.isoformat(),
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

            # 获取所有来源消息的详细信息
            source_messages = []
            if case.source_message_ids:
                source_messages = IPTCCaseService._get_source_messages(db, case.source_message_ids)

            return {
                "id": case.id,
                "title": case.title,
                "content": case.content or "",
                "summary": case.summary or "",
                "source": "IPTC系统",
                "sourceUrl": case.source_url,
                "sourceMessages": source_messages,  # 新增：所有来源消息的详细信息
                "publishDate": case.published_at.isoformat() if case.published_at else case.created_at.isoformat(),
                "published_at": case.published_at.isoformat() if case.published_at else None,
                "viewCount": 0,
                "knowledgePoints": knowledge_points,
                "related_knowledge_points": case.related_knowledge_points or [],
                "primary_region": case.primary_region or "全国",
                "createdAt": case.created_at.isoformat(),
                "created_at": case.created_at.isoformat(),
                "updatedAt": case.updated_at.isoformat(),
                "updated_at": case.updated_at.isoformat(),
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

            # 知识点总数（从ChromaDB查询）
            try:
                chroma_storage = get_chromadb_storage()
                if chroma_storage and chroma_storage.is_initialized():
                    total_kps = chroma_storage.get_collection_count('iptc_knowledge_points')
                else:
                    # 降级到MySQL查询
                    total_kps = db.query(func.count(IPTCKnowledgePointStats.id)).scalar()
            except Exception as e:
                logger.warning(f"从ChromaDB查询知识点数量失败，降级到MySQL: {e}")
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

    @staticmethod
    def delete_case(db: Session, case_id: str) -> bool:
        """
        删除案例

        Args:
            db: 数据库会话
            case_id: 案例ID

        Returns:
            删除成功返回True，案例不存在返回False
        """
        try:
            case = db.query(IPTCCase).filter_by(id=case_id).first()

            if not case:
                return False

            db.delete(case)
            db.commit()
            logger.info(f"成功删除案例: {case_id} - {case.title}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"删除案例失败: {e}")
            raise
