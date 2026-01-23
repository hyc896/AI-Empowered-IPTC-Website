"""
图谱构建服务

本模块负责将提取的实体和关系写入Neo4j图数据库。

主要功能：
- 创建Message节点
- 创建或更新Entity节点（使用MERGE去重）
- 创建MENTIONS关系（Message → Entity）
- 创建Entity间关系（WORKS_AT、INVESTS_IN等）
- 删除消息及其关系

设计原则：
- 使用MERGE避免重复创建实体
- 使用事务函数确保原子性
- 失败降级：单个节点/关系失败不影响整体
- 详细日志记录
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GraphBuilderService:
    """图谱构建服务"""

    def __init__(self, neo4j_storage):
        """初始化图谱构建服务

        Args:
            neo4j_storage: Neo4jStorage实例
        """
        self.neo4j_storage = neo4j_storage

    async def add_message_with_entities(
        self,
        message_id: str,
        message_data: Dict,
        entities: List[Dict],
        relations: List[Dict]
    ) -> Dict[str, int]:
        """添加消息节点及其实体关系

        Args:
            message_id: MySQL消息主键
            message_data: 消息字段字典，包含：
                - source_id: 消息源ID
                - source_name: 消息源名称
                - title: 标题
                - summary: 摘要
                - url: 链接
                - published_at: 发布时间
                - crawled_at: 抓取时间
                - region: 地区（可选）
                - industry_tags: 行业标签（可选）
                - ai_tag: AI标签（可选）
            entities: 实体列表
            relations: 关系列表

        Returns:
            统计信息：
            {
                "message_created": 1,
                "entities_created": 5,
                "mentions_created": 5,
                "relations_created": 3
            }
        """
        stats = {
            "message_created": 0,
            "entities_created": 0,
            "mentions_created": 0,
            "relations_created": 0
        }

        try:
            # 1. 创建Message节点
            await self._create_message_node(message_id, message_data)
            stats["message_created"] = 1

            # 2. 创建或更新Entity节点
            for entity in entities:
                try:
                    created = await self._merge_entity_node(entity)
                    if created:
                        stats["entities_created"] += 1
                except Exception as e:
                    logger.error(f"创建实体节点失败 ({entity.get('name')}): {e}")
                    continue

            # 3. 创建MENTIONS关系
            for entity in entities:
                try:
                    await self._create_mentions_relation(
                        message_id,
                        entity.get('name'),
                        context=None  # 可选：提取上下文片段
                    )
                    stats["mentions_created"] += 1
                except Exception as e:
                    logger.error(f"创建MENTIONS关系失败 ({entity.get('name')}): {e}")
                    continue

            # 4. 创建Entity间关系
            for relation in relations:
                try:
                    await self._create_entity_relation(relation)
                    stats["relations_created"] += 1
                except Exception as e:
                    logger.error(f"创建实体关系失败 ({relation.get('type')}): {e}")
                    continue

            logger.info(
                f"图谱构建完成 (消息ID: {message_id}): "
                f"实体 {stats['entities_created']}, "
                f"提及 {stats['mentions_created']}, "
                f"关系 {stats['relations_created']}"
            )

            return stats

        except Exception as e:
            logger.error(f"图谱构建失败 (消息ID: {message_id}): {e}", exc_info=True)
            return stats

    async def _create_message_node(self, message_id: str, message_data: Dict) -> None:
        """创建消息节点

        Args:
            message_id: 消息ID
            message_data: 消息数据
        """
        query = """
        CREATE (m:Message {
            id: $id,
            name: $name,
            source_id: $source_id,
            source_name: $source_name,
            title: $title,
            summary: $summary,
            url: $url,
            published_at: datetime($published_at),
            crawled_at: datetime($crawled_at),
            region: $region,
            industry_tags: $industry_tags,
            ai_tag: $ai_tag,
            entity_count: $entity_count,
            created_in_graph_at: datetime()
        })
        RETURN m
        """

        # 准备参数
        params = {
            "id": message_id,
            "name": message_data.get("name", ""),
            "source_id": message_data.get("source_id", ""),
            "source_name": message_data.get("source_name", ""),
            "title": message_data.get("title", ""),
            "summary": message_data.get("summary", ""),
            "url": message_data.get("url", ""),
            "published_at": self._format_datetime(message_data.get("published_at")),
            "crawled_at": self._format_datetime(message_data.get("crawled_at")),
            "region": message_data.get("region", ""),
            "industry_tags": message_data.get("industry_tags", ""),
            "ai_tag": message_data.get("ai_tag", ""),
            "entity_count": message_data.get("entity_count", 0)
        }

        await self.neo4j_storage.execute_write_async(query, params)
        logger.debug(f"创建Message节点: {message_id}")

    async def _merge_entity_node(self, entity: Dict) -> bool:
        """创建或更新实体节点

        使用MERGE避免重复创建。
        ON CREATE: 设置初始属性
        ON MATCH: 更新mention_count和aliases

        Args:
            entity: 实体字典

        Returns:
            是否新创建（True=新创建，False=已存在）
        """
        query = """
        MERGE (e:Entity {name: $name})
        ON CREATE SET
            e.id = randomUUID(),
            e.type = $type,
            e.first_mentioned_at = datetime(),
            e.mention_count = 1,
            e.aliases = $aliases,
            e.description = $description,
            e.page_range = $page_range
        ON MATCH SET
            e.mention_count = e.mention_count + 1,
            e.aliases = CASE
                WHEN e.aliases IS NULL THEN $aliases
                ELSE e.aliases + [x IN $aliases WHERE NOT x IN e.aliases]
            END,
            e.page_range = CASE
                WHEN e.page_range IS NULL THEN $page_range
                ELSE e.page_range
            END
        RETURN e, (e.mention_count = 1) as is_new
        """

        # 准备参数
        params = {
            "name": entity.get("name", ""),
            "type": entity.get("type", ""),
            "aliases": entity.get("aliases", []),
            "description": entity.get("attributes", {}).get("description", ""),
            "page_range": entity.get("page_range", "")
        }

        # 添加类型特定的属性
        attributes = entity.get("attributes", {})
        if attributes:
            # 动态添加属性（根据实体类型）
            for key, value in attributes.items():
                if key != "description":
                    query = query.replace(
                        "e.description = $description",
                        f"e.description = $description,\n            e.{key} = ${key}"
                    )
                    params[key] = value

        result = await self.neo4j_storage.execute_write_async(query, params)

        # 判断是否新创建
        is_new = result.get("is_new", True) if result else True

        logger.debug(f"{'创建' if is_new else '更新'}Entity节点: {entity.get('name')}")
        return is_new

    async def _create_mentions_relation(
        self,
        message_id: str,
        entity_name: str,
        context: Optional[str] = None
    ) -> None:
        """创建MENTIONS关系

        Args:
            message_id: 消息ID
            entity_name: 实体名称
            context: 上下文片段（可选）
        """
        query = """
        MATCH (m:Message {id: $message_id})
        MATCH (e:Entity {name: $entity_name})
        CREATE (m)-[:MENTIONS {
            times: 1,
            context: $context,
            created_at: datetime()
        }]->(e)
        """

        params = {
            "message_id": message_id,
            "entity_name": entity_name,
            "context": context or ""
        }

        await self.neo4j_storage.execute_write_async(query, params)
        logger.debug(f"创建MENTIONS关系: {message_id} → {entity_name}")

    async def _create_entity_relation(self, relation: Dict) -> None:
        """创建实体间关系

        Args:
            relation: 关系字典，包含：
                - source: 源实体名称
                - target: 目标实体名称
                - type: 关系类型
                - properties: 关系属性（可选）
        """
        source = relation.get("source", "")
        target = relation.get("target", "")
        rel_type = relation.get("type", "")
        properties = relation.get("properties", {})

        if not source or not target or not rel_type:
            logger.warning(f"关系信息不完整: {relation}")
            return

        # 构建属性字符串
        props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
        if props_str:
            props_str = "{" + props_str + ", created_at: datetime()}"
        else:
            props_str = "{created_at: datetime()}"

        query = f"""
        MATCH (s:Entity {{name: $source}})
        MATCH (t:Entity {{name: $target}})
        CREATE (s)-[:{rel_type} {props_str}]->(t)
        """

        params = {
            "source": source,
            "target": target,
            **properties
        }

        await self.neo4j_storage.execute_write_async(query, params)
        logger.debug(f"创建{rel_type}关系: {source} → {target}")

    async def delete_message_graph(self, message_id: str) -> Dict[str, int]:
        """删除消息及其关系

        使用DETACH DELETE删除节点及其所有关系。

        Args:
            message_id: 消息ID

        Returns:
            统计信息
        """
        query = """
        MATCH (m:Message {id: $message_id})
        DETACH DELETE m
        """

        params = {"message_id": message_id}

        result = await self.neo4j_storage.execute_write_async(query, params)

        logger.info(f"删除Message节点及其关系: {message_id}")

        return {
            "nodes_deleted": result.get("nodes_deleted", 0),
            "relationships_deleted": result.get("relationships_deleted", 0)
        }

    async def get_message_entities(self, message_id: str) -> List[Dict]:
        """获取消息提及的所有实体

        Args:
            message_id: 消息ID

        Returns:
            实体列表
        """
        query = """
        MATCH (m:Message {id: $message_id})-[:MENTIONS]->(e:Entity)
        RETURN e.name as name, e.type as type, e.mention_count as mention_count
        ORDER BY e.mention_count DESC
        """

        params = {"message_id": message_id}

        results = await self.neo4j_storage.execute_read_async(query, params)

        return results

    async def get_entity_messages(
        self,
        entity_name: str,
        limit: int = 20
    ) -> List[Dict]:
        """获取提及某个实体的所有消息

        Args:
            entity_name: 实体名称
            limit: 返回数量限制

        Returns:
            消息列表
        """
        query = """
        MATCH (e:Entity {name: $entity_name})<-[:MENTIONS]-(m:Message)
        RETURN m.id as id, m.title as title, m.published_at as published_at, m.url as url
        ORDER BY m.published_at DESC
        LIMIT $limit
        """

        params = {
            "entity_name": entity_name,
            "limit": limit
        }

        results = await self.neo4j_storage.execute_read_async(query, params)

        return results

    def _format_datetime(self, dt) -> str:
        """格式化日期时间为ISO 8601字符串

        Args:
            dt: datetime对象或字符串

        Returns:
            ISO 8601格式字符串
        """
        if dt is None or dt == "":
            return datetime.now().isoformat()

        if isinstance(dt, datetime):
            return dt.isoformat()

        if isinstance(dt, str):
            # 如果字符串为空，返回当前时间
            if not dt.strip():
                return datetime.now().isoformat()
            return dt

        return datetime.now().isoformat()
