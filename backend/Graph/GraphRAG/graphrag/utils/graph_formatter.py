"""
图数据格式转换器

本模块负责将Neo4j图数据转换为前端可视化库（ECharts、D3.js）所需的格式。

主要功能：
- Neo4j节点和关系 → ECharts Graph格式
- 节点大小计算（基于mention_count）
- 节点分类和颜色映射
- 关系标签格式化
"""

from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class GraphFormatter:
    """图数据格式转换器"""

    # 实体类型到分类索引的映射
    ENTITY_TYPE_CATEGORY = {
        "Company": 0,
        "Person": 1,
        "Technology": 2,
        "Product": 3,
        "Organization": 4,
        "Event": 5,
        "Concept": 6,
        "Location": 7
    }

    # 分类名称（用于图例）
    CATEGORIES = [
        {"name": "公司"},
        {"name": "人物"},
        {"name": "技术"},
        {"name": "产品"},
        {"name": "组织"},
        {"name": "事件"},
        {"name": "概念"},
        {"name": "地点"}
    ]

    @staticmethod
    def to_echarts_format(
        nodes: List[Dict],
        relationships: List[Dict]
    ) -> Dict[str, Any]:
        """转换为ECharts Graph格式

        Args:
            nodes: Neo4j节点列表，每个节点包含：
                - id: 节点ID
                - name: 节点名称
                - type: 节点类型
                - mention_count: 提及次数（可选）
            relationships: Neo4j关系列表，每个关系包含：
                - source: 源节点ID
                - target: 目标节点ID
                - type: 关系类型
                - properties: 关系属性（可选）

        Returns:
            ECharts Graph格式：
            {
                "nodes": [
                    {
                        "id": "entity-uuid-1",
                        "name": "OpenAI",
                        "category": 0,
                        "symbolSize": 50,
                        "value": 150,
                        "label": {"show": true}
                    }
                ],
                "links": [
                    {
                        "source": "entity-uuid-1",
                        "target": "entity-uuid-2",
                        "value": "INVESTS_IN",
                        "label": {"show": true, "formatter": "投资"}
                    }
                ],
                "categories": [
                    {"name": "公司"},
                    {"name": "人物"}
                ]
            }
        """
        # 转换节点
        echarts_nodes = []
        for node in nodes:
            echarts_node = GraphFormatter._format_node(node)
            echarts_nodes.append(echarts_node)

        # 转换关系
        echarts_links = []
        for rel in relationships:
            echarts_link = GraphFormatter._format_relationship(rel)
            echarts_links.append(echarts_link)

        return {
            "nodes": echarts_nodes,
            "links": echarts_links,
            "categories": GraphFormatter.CATEGORIES
        }

    @staticmethod
    def _format_node(node: Dict) -> Dict:
        """格式化单个节点

        Args:
            node: Neo4j节点

        Returns:
            ECharts节点格式
        """
        node_id = node.get("id", "")
        name = node.get("name", "")
        node_type = node.get("type", "")
        mention_count = node.get("mention_count", 1)

        # 计算节点大小（基于提及次数）
        symbol_size = GraphFormatter._calculate_symbol_size(mention_count)

        # 获取分类索引
        category = GraphFormatter.ENTITY_TYPE_CATEGORY.get(node_type, 0)

        return {
            "id": node_id,
            "name": name,
            "category": category,
            "symbolSize": symbol_size,
            "value": mention_count,
            "label": {
                "show": True
            },
            "itemStyle": {
                "borderWidth": 2
            }
        }

    @staticmethod
    def _format_relationship(rel: Dict) -> Dict:
        """格式化单个关系

        Args:
            rel: Neo4j关系

        Returns:
            ECharts链接格式
        """
        source = rel.get("source", "")
        target = rel.get("target", "")
        rel_type = rel.get("type", "")
        properties = rel.get("properties", {})

        # 格式化关系标签
        label_text = GraphFormatter._format_relation_label(rel_type, properties)

        return {
            "source": source,
            "target": target,
            "value": rel_type,
            "label": {
                "show": True,
                "formatter": label_text
            },
            "lineStyle": {
                "curveness": 0.2
            }
        }

    @staticmethod
    def _calculate_symbol_size(mention_count: int) -> int:
        """计算节点大小

        基于提及次数的对数缩放，避免节点过大或过小。

        Args:
            mention_count: 提及次数

        Returns:
            节点大小（像素）
        """
        import math

        # 最小和最大节点大小
        min_size = 20
        max_size = 80

        # 对数缩放
        if mention_count <= 1:
            return min_size

        # log10缩放
        size = min_size + (max_size - min_size) * (math.log10(mention_count) / math.log10(100))

        return int(min(max(size, min_size), max_size))

    @staticmethod
    def _format_relation_label(rel_type: str, properties: Dict) -> str:
        """格式化关系标签

        Args:
            rel_type: 关系类型
            properties: 关系属性

        Returns:
            格式化后的标签文本
        """
        # 关系类型中文映射
        type_labels = {
            "WORKS_AT": "任职",
            "INVESTS_IN": "投资",
            "DEVELOPS": "开发",
            "COMPETES_WITH": "竞争",
            "PARTNERS_WITH": "合作",
            "BASED_ON": "基于",
            "LOCATED_IN": "位于"
        }

        label = type_labels.get(rel_type, rel_type)

        # 添加属性信息
        if properties:
            # 提取关键属性
            if "role" in properties:
                label += f" ({properties['role']})"
            elif "amount" in properties:
                label += f" ({properties['amount']})"

        return label

    @staticmethod
    def to_d3_format(
        nodes: List[Dict],
        relationships: List[Dict]
    ) -> Dict[str, Any]:
        """转换为D3.js Force Graph格式

        Args:
            nodes: Neo4j节点列表
            relationships: Neo4j关系列表

        Returns:
            D3.js格式：
            {
                "nodes": [{"id": "1", "name": "OpenAI", "group": 1}],
                "links": [{"source": "1", "target": "2", "value": 1}]
            }
        """
        # 转换节点
        d3_nodes = []
        for node in nodes:
            d3_node = {
                "id": node.get("id", ""),
                "name": node.get("name", ""),
                "group": GraphFormatter.ENTITY_TYPE_CATEGORY.get(node.get("type", ""), 0),
                "value": node.get("mention_count", 1)
            }
            d3_nodes.append(d3_node)

        # 转换关系
        d3_links = []
        for rel in relationships:
            d3_link = {
                "source": rel.get("source", ""),
                "target": rel.get("target", ""),
                "value": 1,
                "type": rel.get("type", "")
            }
            d3_links.append(d3_link)

        return {
            "nodes": d3_nodes,
            "links": d3_links
        }
