# -*- coding: utf-8 -*-

"""
消息检索服务
提供统一的消息检索接口，支持MySQL+ChromaDB并发查询
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from ..database.connection import create_session
from ..database.entities import MessageSource, TongHuaShunMessage, Kr36Message, ArxivMessage, ExternalMessage

logger = logging.getLogger(__name__)


def _load_platform_config() -> dict:
    """加载消息平台配置"""
    try:
        import yaml
        import os
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.yaml')

        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        return config_data
    except Exception as e:
        logger.error(f"加载平台配置失败: {e}")
        return {}


class SearchService:
    """消息检索服务"""

    def __init__(self):
        """初始化检索服务"""
        # 使用消息平台自己的配置系统
        try:
            # 从消息平台配置加载参数
            config = _load_platform_config()

            self.similarity_threshold = config.get("retrieval.similarity_threshold", 0.4)
            self.rrf_k = config.get("retrieval.rrf_k", 60)
            self.max_results = config.get("retrieval.max_results", 100)
            self.search_timeout = config.get("retrieval.search_timeout", 30)

            # 初始化ChromaDB存储
            try:
                from backend.storage import get_chromadb_storage
                self.chroma_storage = get_chromadb_storage()
            except ImportError:
                logger.warning("【检索服务】ChromaDB存储初始化失败，将只使用MySQL检索")
                self.chroma_storage = None

            # 初始化Embedding客户端
            try:
                from backend.llm import get_embedding_client
                self.embedding_client = get_embedding_client()
            except ImportError:
                logger.warning("【检索服务】Embedding客户端初始化失败，将只支持关键词检索")
                self.embedding_client = None

        except Exception as e:
            logger.error(f"【检索服务】初始化失败: {e}")
            # 使用默认值
            self.similarity_threshold = 0.4
            self.rrf_k = 60
            self.max_results = 100
            self.search_timeout = 30
            self.chroma_storage = None
            self.embedding_client = None

    async def search(
        self,
        source_type: Optional[str] = None,
        query: str = "",
        time_range: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        并发检索MySQL + ChromaDB

        Args:
            source_type: 类别标识（news/wechat/rss）
            query: 检索关键词
            time_range: 时间范围，如 {"hours": 24} 表示最近24小时
            limit: 返回结果数量
            **kwargs: 其他参数

        Returns:
            检索结果列表
        """
        start_time = datetime.now()
        logger.info(f"【消息检索】开始检索 - 类别: {source_type}, 关键词: '{query}', 限制: {limit}")

        if not query or not query.strip():
            logger.warning("【消息检索】查询关键词为空，返回空结果")
            return []

        try:
            # 获取消息源配置
            sources = await self._get_sources_by_type(source_type)

            if not sources:
                logger.warning(f"【消息检索】未找到类别 {source_type} 的激活消息源")
                return []

            logger.info(f"【消息检索】找到 {len(sources)} 个消息源: {', '.join([s['display_name'] for s in sources])}")

            # 创建并发检索任务
            tasks = []
            for source in sources:
                display_name = source.get('display_name', source['name'])
                logger.info(f"【任务创建】为消息源 {display_name} 创建 MySQL + ChromaDB 并发检索任务")

                # MySQL检索任务
                mysql_task = self._search_mysql(
                    table_name=source['mysql_table'],
                    query=query,
                    time_range=time_range,
                    limit=limit,
                    display_name=display_name
                )

                # ChromaDB检索任务（如果可用）
                if self.chroma_storage and self.embedding_client:
                    # 生成查询向量
                    if not hasattr(self, '_query_embedding') or self._query_embedding is None:
                        logger.info(f"【向量化】正在生成查询向量: '{query}'")
                        self._query_embedding = self.embedding_client.generate_embedding(query)
                        logger.info(f"【向量化】查询向量生成完成 (维度: {len(self._query_embedding)})")

                    chroma_task = self._search_chroma(
                        collection_name=source['chroma_collection'],
                        query_embedding=self._query_embedding,
                        limit=limit,
                        display_name=display_name,
                        similarity_threshold=self.similarity_threshold
                    )
                else:
                    # 创建空的ChromaDB任务
                    chroma_task = asyncio.create_task(self._empty_chroma_search(display_name))

                tasks.extend([mysql_task, chroma_task])

            # 执行并发检索
            logger.info(f"【并发执行】开始执行 {len(tasks)} 个检索任务...")
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 收集结果
            all_results = []
            mysql_count = 0
            chroma_count = 0

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"【检索失败】任务执行失败: {result}")
                    continue

                if isinstance(result, list):
                    for item in result:
                        if item.get('source') == 'mysql':
                            mysql_count += 1
                        elif item.get('source') == 'chromadb':
                            chroma_count += 1
                    all_results.extend(result)

            logger.info(f"【检索完成】MySQL: {mysql_count} 条, ChromaDB: {chroma_count} 条, 总计: {len(all_results)} 条")

            # RRF融合
            if all_results:
                logger.info(f"【结果融合】使用 RRF 算法融合 {len(all_results)} 条结果（k={self.rrf_k}）...")
                fused_results = self._rrf_fusion(all_results, k=self.rrf_k)
                logger.info(f"【结果融合】去重后剩余 {len(fused_results)} 条结果")

                # 按时间排序
                fused_results.sort(
                    key=lambda x: x.get('published_at') or datetime.min,
                    reverse=True
                )

                final_results = fused_results[:limit]
            else:
                final_results = []

            # 记录检索耗时
            search_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"【返回结果】最终返回 {len(final_results)} 条结果，耗时 {search_time:.2f}s")

            return final_results

        except Exception as e:
            logger.error(f"【消息检索】检索失败: {e}", exc_info=True)
            return []

    async def _get_sources_by_type(self, source_type: Optional[str]) -> List[Dict[str, Any]]:
        """获取指定业务类别的所有消息源"""
        try:
            with create_session() as db:
                query = db.query(MessageSource).filter(MessageSource.is_active == True)

                if source_type:
                    query = query.filter(MessageSource.category == source_type)

                sources = query.all()

                result = []
                for source in sources:
                    config = source.config or {}
                    result.append({
                        "id": source.id,
                        "name": source.name,
                        "adapter_name": source.adapter_name,
                        "category": source.category or config.get("source_type", "unknown"),
                        "display_name": source.display_name or source.name,
                        "mysql_table": config.get("mysql_table", f"{source.name}_messages"),
                        "chroma_collection": config.get("chroma_collection", f"mp_{source.name}"),
                        "collector_module": config.get("collector_module", ""),
                        "config": config
                    })

                return result

        except Exception as e:
            logger.error(f"【消息检索】获取消息源失败: {e}")
            return []

    async def _search_mysql(
        self,
        table_name: str,
        query: str,
        time_range: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        display_name: str = ""
    ) -> List[Dict[str, Any]]:
        """MySQL关键词搜索"""
        try:
            logger.info(f"【MySQL检索】{display_name} - 表: {table_name}, 关键词: '{query}'")

            # 表到模型的映射
            from ..database.entities import TongHuaShunMessage, Kr36Message, ArxivMessage, ExternalMessage
            from sqlalchemy import or_

            model_map = {
                "mp_tonghuashun_messages": TongHuaShunMessage,
                "mp_kr36_messages": Kr36Message,
                "mp_arxiv_messages": ArxivMessage,
                "mp_external_messages": ExternalMessage
            }

            model = model_map.get(table_name)
            if not model:
                logger.warning(f"【MySQL检索】未找到表 {table_name} 的 ORM 模型")
                return []

            with create_session() as db:
                # 解析多关键词（按空格分割）
                keywords = [kw.strip() for kw in query.split() if kw.strip()]

                if len(keywords) == 1:
                    # 单关键词
                    query_filter = or_(
                        model.title.like(f"%{keywords[0]}%"),
                        model.content.like(f"%{keywords[0]}%")
                    )
                    logger.info(f"【MySQL检索】{display_name} - 单关键词: '{keywords[0]}'")
                else:
                    # 多关键词：OR查询
                    keyword_filters = []
                    for kw in keywords:
                        keyword_filters.append(or_(
                            model.title.like(f"%{kw}%"),
                            model.content.like(f"%{kw}%")
                        ))
                    query_filter = or_(*keyword_filters)
                    logger.info(f"【MySQL检索】{display_name} - 多关键词OR查询: {keywords} (共{len(keywords)}个)")

                # 时间过滤
                time_filter_desc = ""
                if time_range and "hours" in time_range:
                    hours = time_range["hours"]
                    time_threshold = datetime.now() - timedelta(hours=hours)
                    query_filter = query_filter & (model.published_at >= time_threshold)
                    time_filter_desc = f", 时间范围: 最近{hours}小时"

                logger.info(f"【MySQL检索】{display_name} - 执行查询{time_filter_desc}")

                results = db.query(model).filter(query_filter).order_by(
                    model.published_at.desc()
                ).limit(limit).all()

                logger.info(f"【MySQL检索】{display_name} - 找到 {len(results)} 条结果")

                # 格式化结果
                formatted_results = []
                for result in results:
                    # 通用字段
                    item = {
                        "id": result.id,
                        "title": f"【{display_name}】{result.title}",
                        "content": result.content,
                        "published_at": result.published_at,
                        "source": "mysql",
                        "source_name": display_name,
                        "table_name": table_name
                    }

                    # URL字段适配
                    if hasattr(result, 'url'):
                        item["url"] = result.url
                    elif hasattr(result, 'source_url'):
                        item["url"] = result.source_url
                    else:
                        item["url"] = ""

                    # Provider字段适配
                    if hasattr(result, 'provider'):
                        item["provider"] = result.provider
                    else:
                        item["provider"] = display_name

                    formatted_results.append(item)

                return formatted_results

        except Exception as e:
            logger.error(f"【MySQL检索】{display_name} - 检索失败: {e}")
            return []

    async def _search_chroma(
        self,
        collection_name: str,
        query_embedding: List[float],
        limit: int = 20,
        display_name: str = "",
        similarity_threshold: float = 0.4
    ) -> List[Dict[str, Any]]:
        """ChromaDB语义检索"""
        try:
            logger.info(f"【向量检索】{display_name} - Collection: {collection_name}, 向量维度: {len(query_embedding)}, 相似度阈值: {similarity_threshold}")

            if not self.chroma_storage:
                logger.warning(f"【向量检索】{display_name} - ChromaDB存储未初始化")
                return []

            results = self.chroma_storage.search(
                collection_name=collection_name,
                query_embeddings=[query_embedding],
                n_results=limit
            )

            if not results or "ids" not in results:
                logger.info(f"【向量检索】{display_name} - 未找到结果")
                return []

            result_count = len(results["ids"][0])
            logger.info(f"【向量检索】{display_name} - 原始检索到 {result_count} 条结果")

            formatted_results = []
            filtered_count = 0

            for i in range(result_count):
                metadata = results["metadatas"][0][i] if "metadatas" in results else {}

                # 解析发布时间
                published_at_str = metadata.get("published_at")
                published_at = None
                if published_at_str:
                    try:
                        from dateutil import parser
                        published_at = parser.isoparse(published_at_str)
                    except:
                        pass

                title = metadata.get("title", "")
                distance = results["distances"][0][i] if "distances" in results else None
                similarity = 1 - distance if distance is not None else 0.0

                if i < 3:
                    logger.info(f"【向量检索】{display_name} - 结果 #{i+1}: 相似度={similarity:.4f}, 标题='{title[:30]}...'")

                # 相似度阈值过滤
                if similarity < similarity_threshold:
                    filtered_count += 1
                    continue

                result = {
                    "id": results["ids"][0][i],
                    "title": f"【{display_name}】{title}",
                    "content": results["documents"][0][i],
                    "url": metadata.get("url", ""),
                    "published_at": published_at,
                    "provider": metadata.get("provider", ""),
                    "distance": distance,
                    "similarity": similarity,
                    "source": "chromadb",
                    "source_name": display_name,
                    "collection_name": collection_name
                }
                formatted_results.append(result)

            if filtered_count > 0:
                logger.info(f"【向量检索】{display_name} - 过滤掉 {filtered_count} 条低相似度结果（< {similarity_threshold}），保留 {len(formatted_results)} 条")
            else:
                logger.info(f"【向量检索】{display_name} - 全部 {len(formatted_results)} 条结果均满足相似度要求")

            return formatted_results

        except Exception as e:
            logger.error(f"【向量检索】{display_name} - 检索失败: {e}")
            return []

    async def _empty_chroma_search(self, display_name: str) -> List[Dict[str, Any]]:
        """空的ChromaDB搜索（当ChromaDB不可用时）"""
        logger.info(f"【向量检索】{display_name} - ChromaDB不可用，跳过向量检索")
        return []

    def _rrf_fusion(
        self,
        results: List[Dict[str, Any]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """RRF (Reciprocal Rank Fusion) 融合算法"""
        key_to_doc = {}
        key_scores = defaultdict(float)

        for rank, doc in enumerate(results):
            # 构建去重Key
            dedup_key = doc.get("url") or doc.get("id") or doc.get("title", "")

            if not dedup_key:
                import hashlib
                content_hash = hashlib.md5(
                    f"{doc.get('title', '')}{doc.get('content', '')}".encode()
                ).hexdigest()
                dedup_key = content_hash

            # 计算RRF分数
            score = 1.0 / (k + rank + 1)
            key_scores[dedup_key] += score

            if dedup_key not in key_to_doc:
                key_to_doc[dedup_key] = doc

        # 构建融合结果
        fused = [
            {**key_to_doc[key], "rrf_score": score}
            for key, score in key_scores.items()
        ]

        # 按RRF分数排序
        fused.sort(key=lambda x: x["rrf_score"], reverse=True)

        return fused

    async def get_sources(self, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        """获取消息源列表"""
        try:
            with create_session() as db:
                query = db.query(MessageSource)
                if is_active is not None:
                    query = query.filter(MessageSource.is_active == is_active)

                sources = query.all()

                result = []
                for source in sources:
                    config = source.config or {}
                    result.append({
                        "id": source.id,
                        "name": source.name,
                        "adapter_name": source.adapter_name,
                        "category": source.category,
                        "display_name": source.display_name,
                        "config": config,
                        "is_active": source.is_active,
                        "last_crawled_at": source.last_crawled_at,
                        "created_at": source.created_at,
                        "updated_at": source.updated_at
                    })

                return result

        except Exception as e:
            logger.error(f"【消息检索】获取消息源列表失败: {e}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            with create_session() as db:
                # 统计各表记录数
                stats = {}

                # 消息源统计
                stats["sources"] = {
                    "total": db.query(MessageSource).count(),
                    "active": db.query(MessageSource).filter(MessageSource.is_active == True).count()
                }

                # 消息表统计
                from ..database.entities import TongHuaShunMessage, Kr36Message, ArxivMessage, ExternalMessage

                stats["messages"] = {
                    "tonghuashun": db.query(TongHuaShunMessage).count(),
                    "kr36": db.query(Kr36Message).count(),
                    "arxiv": db.query(ArxivMessage).count(),
                    "external": db.query(ExternalMessage).count()
                }

                # 总消息数
                stats["messages"]["total"] = sum(stats["messages"].values())

                # 最近24小时消息数
                from datetime import datetime, timedelta
                yesterday = datetime.now() - timedelta(hours=24)

                stats["recent_messages"] = {
                    "tonghuashun": db.query(TongHuaShunMessage).filter(TongHuaShunMessage.crawled_at >= yesterday).count(),
                    "kr36": db.query(Kr36Message).filter(Kr36Message.crawled_at >= yesterday).count(),
                    "arxiv": db.query(ArxivMessage).filter(ArxivMessage.crawled_at >= yesterday).count(),
                    "external": db.query(ExternalMessage).filter(ExternalMessage.crawled_at >= yesterday).count()
                }

                stats["recent_messages"]["total"] = sum(stats["recent_messages"].values())

                return stats

        except Exception as e:
            logger.error(f"【消息检索】获取统计信息失败: {e}")
            return {}


# 全局检索服务实例
search_service = SearchService()