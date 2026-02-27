# -*- coding: utf-8 -*-
"""
知识图谱服务
提供知识图谱数据查询功能
"""
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加GraphRAG到Python路径
graphrag_path = Path(__file__).parent.parent / "Graph" / "GraphRAG"
sys.path.insert(0, str(graphrag_path))

from graphrag.core.storage import Neo4jStorage
from graphrag.utils.config_loader import ConfigLoader

logger = logging.getLogger(__name__)


class GraphService:
    """知识图谱服务类"""

    def __init__(self):
        """初始化服务"""
        self.storage: Optional[Neo4jStorage] = None
        self._initialized = False

    def initialize(self):
        """初始化Neo4j连接"""
        if self._initialized:
            return

        try:
            # 加载配置
            config_path = Path(__file__).parent.parent / "Graph" / "GraphRAG" / "config" / "default_config.yaml"
            config = ConfigLoader.load_config(str(config_path))

            # 初始化存储
            self.storage = Neo4jStorage()
            self.storage.initialize(config['neo4j'])
            self._initialized = True

            logger.info("知识图谱服务初始化成功")
        except Exception as e:
            logger.error(f"知识图谱服务初始化失败: {e}", exc_info=True)
            raise

    def close(self):
        """关闭连接"""
        if self.storage:
            self.storage.close()
            self._initialized = False

    def get_book_list(self) -> List[Dict[str, Any]]:
        """获取书籍列表

        Returns:
            书籍列表，包含书籍ID、名称、统计信息（去重后）
        """
        if not self._initialized:
            self.initialize()

        query = """
        MATCH (b:Book)
        OPTIONAL MATCH (b)-[:HAS_CHAPTER]->(c:Chapter)
        OPTIONAL MATCH (c)-[:HAS_SECTION]->(s:Section)
        OPTIONAL MATCH (s)-[:HAS_KNOWLEDGE_POINT]->(k:KnowledgePoint)
        WITH b,
             count(DISTINCT c) as chapter_count,
             count(DISTINCT s) as section_count,
             count(DISTINCT k) as knowledge_point_count
        RETURN b.id as book_id,
               b.name as book_name,
               chapter_count,
               section_count,
               knowledge_point_count
        ORDER BY b.id
        """

        try:
            results = self.storage.execute_read(query)
            books = []
            book_names_seen = {}  # 用于去重：book_name -> book_data

            for record in results:
                book_name = record['book_name']
                entity_count = record['knowledge_point_count']

                # 如果书名已存在，保留实体数量多的那本
                if book_name in book_names_seen:
                    if entity_count > book_names_seen[book_name]['entity_count']:
                        book_names_seen[book_name] = {
                            'book_id': record['book_id'],
                            'book_name': book_name,
                            'entity_count': entity_count,
                            'relation_count': record['section_count'] + record['chapter_count'],
                            'upload_time': '2026-02-07'
                        }
                else:
                    book_names_seen[book_name] = {
                        'book_id': record['book_id'],
                        'book_name': book_name,
                        'entity_count': entity_count,
                        'relation_count': record['section_count'] + record['chapter_count'],
                        'upload_time': '2026-02-07'
                    }

            books = list(book_names_seen.values())
            return books
        except Exception as e:
            logger.error(f"获取书籍列表失败: {e}", exc_info=True)
            raise

    def get_book_graph(self, book_id: str) -> Dict[str, Any]:
        """获取指定书籍的知识图谱（层次化结构）

        Args:
            book_id: 书籍ID

        Returns:
            图谱数据，包含节点和边（书→章→节→知识点的层次结构）
        """
        if not self._initialized:
            self.initialize()

        # 查询书籍的完整层次结构
        query = """
        MATCH (b:Book {id: $book_id})
        OPTIONAL MATCH (b)-[:HAS_CHAPTER]->(c:Chapter)
        OPTIONAL MATCH (c)-[:HAS_SECTION]->(s:Section)
        OPTIONAL MATCH (s)-[:HAS_KNOWLEDGE_POINT]->(k:KnowledgePoint)
        RETURN b, c, s, k
        """

        try:
            results = self.storage.execute_read(query, {'book_id': book_id})

            nodes = []
            edges = []
            node_ids = set()

            for record in results:
                # 1. 添加书籍节点（中心节点）
                if record.get('b'):
                    b = record['b']
                    book_node_id = f"book_{b['id']}"
                    if book_node_id not in node_ids:
                        nodes.append({
                            'id': book_node_id,
                            'label': b['name'],
                            'type': 'book',
                            'size': 80,
                            'data': {
                                'name': b['name'],
                                'id': b['id']
                            }
                        })
                        node_ids.add(book_node_id)

                # 2. 添加章节点
                if record.get('c'):
                    c = record['c']
                    chapter_id = f"chapter_{c['id']}"
                    if chapter_id not in node_ids:
                        nodes.append({
                            'id': chapter_id,
                            'label': c['name'],
                            'type': 'chapter',
                            'size': 60,
                            'data': {
                                'name': c['name'],
                                'id': c['id']
                            }
                        })
                        node_ids.add(chapter_id)

                        # 添加书→章的边
                        if record.get('b'):
                            b = record['b']
                            edges.append({
                                'id': f"book_{b['id']}_chapter_{c['id']}",
                                'source': f"book_{b['id']}",
                                'target': chapter_id,
                                'type': 'has-chapter'
                            })

                # 3. 添加节节点
                if record.get('s'):
                    s = record['s']
                    section_id = f"section_{s['id']}"
                    if section_id not in node_ids:
                        nodes.append({
                            'id': section_id,
                            'label': s['name'],
                            'type': 'section',
                            'size': 40,
                            'data': {
                                'name': s['name'],
                                'id': s['id']
                            }
                        })
                        node_ids.add(section_id)

                        # 添加章→节的边
                        if record.get('c'):
                            c = record['c']
                            edges.append({
                                'id': f"chapter_{c['id']}_section_{s['id']}",
                                'source': f"chapter_{c['id']}",
                                'target': section_id,
                                'type': 'has-section'
                            })

                # 4. 添加知识点节点
                if record.get('k'):
                    k = record['k']
                    kp_id = f"kp_{k['name']}"
                    if kp_id not in node_ids:
                        nodes.append({
                            'id': kp_id,
                            'label': k['name'],
                            'type': 'knowledge',
                            'size': 30,
                            'data': {
                                'name': k['name'],
                                'description': k.get('theory_description', ''),
                                'application': k.get('application_scenarios', '')
                            }
                        })
                        node_ids.add(kp_id)

                        # 添加节→知识点的边
                        if record.get('s'):
                            s = record['s']
                            edges.append({
                                'id': f"section_{s['id']}_kp_{k['name']}",
                                'source': f"section_{s['id']}",
                                'target': kp_id,
                                'type': 'has-knowledge-point'
                            })

            return {
                'nodes': nodes,
                'edges': edges
            }
        except Exception as e:
            logger.error(f"获取书籍图谱失败: {e}", exc_info=True)
            raise

    def get_node_subgraph(self, node_id: str, book_id: Optional[str] = None, depth: int = 1) -> Dict[str, Any]:
        """获取以指定节点为中心的子图

        Args:
            node_id: 节点ID（格式：kp_知识点名称 或 kw_关键词名称）
            book_id: 书籍ID（可选，用于限制范围）
            depth: 扩展深度

        Returns:
            子图数据，包含节点和边
        """
        if not self._initialized:
            self.initialize()

        # 解析节点ID
        if node_id.startswith('kp_'):
            node_name = node_id[3:]
            node_label = 'KnowledgePoint'
        elif node_id.startswith('kw_'):
            node_name = node_id[3:]
            node_label = 'Keyword'
        else:
            raise ValueError(f"无效的节点ID格式: {node_id}")

        # 构建查询，获取指定深度的邻居节点
        query = f"""
        MATCH (center:{node_label} {{name: $node_name}})
        CALL apoc.path.subgraphAll(center, {{
            maxLevel: $depth,
            relationshipFilter: "HAS_KEYWORD|HAS_KNOWLEDGE_POINT"
        }})
        YIELD nodes, relationships
        RETURN nodes, relationships
        """

        try:
            results = self.storage.execute_read(query, {
                'node_name': node_name,
                'depth': depth
            })

            nodes = []
            edges = []
            node_ids = set()

            for record in results:
                # 处理节点
                for node in record.get('nodes', []):
                    labels = list(node.labels)
                    if 'KnowledgePoint' in labels:
                        node_id = f"kp_{node['name']}"
                        if node_id not in node_ids:
                            nodes.append({
                                'id': node_id,
                                'label': node['name'],
                                'type': 'knowledge',
                                'data': {
                                    'name': node['name'],
                                    'description': node.get('theory_description', ''),
                                    'application': node.get('application_scenarios', '')
                                }
                            })
                            node_ids.add(node_id)
                    elif 'Keyword' in labels:
                        node_id = f"kw_{node['name']}"
                        if node_id not in node_ids:
                            nodes.append({
                                'id': node_id,
                                'label': node['name'],
                                'type': 'keyword',
                                'size': 20
                            })
                            node_ids.add(node_id)

                # 处理关系
                for rel in record.get('relationships', []):
                    start_node = rel.start_node
                    end_node = rel.end_node

                    start_labels = list(start_node.labels)
                    end_labels = list(end_node.labels)

                    if 'KnowledgePoint' in start_labels:
                        source_id = f"kp_{start_node['name']}"
                    elif 'Keyword' in start_labels:
                        source_id = f"kw_{start_node['name']}"
                    else:
                        continue

                    if 'KnowledgePoint' in end_labels:
                        target_id = f"kp_{end_node['name']}"
                    elif 'Keyword' in end_labels:
                        target_id = f"kw_{end_node['name']}"
                    else:
                        continue

                    edge_id = f"{source_id}_{target_id}"
                    edges.append({
                        'id': edge_id,
                        'source': source_id,
                        'target': target_id,
                        'type': rel.type.lower()
                    })

            return {
                'nodes': nodes,
                'edges': edges
            }
        except Exception as e:
            logger.error(f"获取节点子图失败: {e}", exc_info=True)
            # 如果APOC不可用，使用简单查询
            return self._get_node_subgraph_simple(node_id, node_name, node_label, depth)

    def _get_node_subgraph_simple(self, node_id: str, node_name: str, node_label: str, depth: int) -> Dict[str, Any]:
        """使用简单查询获取节点子图（APOC不可用时的后备方案）

        Args:
            node_id: 节点ID
            node_name: 节点名称
            node_label: 节点标签
            depth: 扩展深度

        Returns:
            子图数据
        """
        # 使用简单的MATCH查询
        if node_label == 'KnowledgePoint':
            query = """
            MATCH (k:KnowledgePoint {name: $node_name})
            OPTIONAL MATCH (k)-[:HAS_KEYWORD]->(kw:Keyword)
            RETURN k, collect(DISTINCT kw) as keywords
            """
        else:  # Keyword
            query = """
            MATCH (kw:Keyword {name: $node_name})
            OPTIONAL MATCH (k:KnowledgePoint)-[:HAS_KEYWORD]->(kw)
            RETURN kw, collect(DISTINCT k) as knowledge_points
            """

        try:
            results = self.storage.execute_read(query, {'node_name': node_name})

            nodes = []
            edges = []
            node_ids = set()

            for record in results:
                if node_label == 'KnowledgePoint':
                    # 添加中心知识点节点
                    k = record['k']
                    kp_id = f"kp_{k['name']}"
                    nodes.append({
                        'id': kp_id,
                        'label': k['name'],
                        'type': 'knowledge',
                        'data': {
                            'name': k['name'],
                            'description': k.get('theory_description', ''),
                            'application': k.get('application_scenarios', '')
                        }
                    })
                    node_ids.add(kp_id)

                    # 添加关键词节点
                    for kw in record.get('keywords', []):
                        if kw:
                            kw_id = f"kw_{kw['name']}"
                            if kw_id not in node_ids:
                                nodes.append({
                                    'id': kw_id,
                                    'label': kw['name'],
                                    'type': 'keyword',
                                    'size': 20
                                })
                                node_ids.add(kw_id)

                            # 添加边
                            edges.append({
                                'id': f"{kp_id}_{kw_id}",
                                'source': kp_id,
                                'target': kw_id,
                                'type': 'has-keyword'
                            })
                else:  # Keyword
                    # 添加中心关键词节点
                    kw = record['kw']
                    kw_id = f"kw_{kw['name']}"
                    nodes.append({
                        'id': kw_id,
                        'label': kw['name'],
                        'type': 'keyword',
                        'size': 20
                    })
                    node_ids.add(kw_id)

                    # 添加知识点节点
                    for k in record.get('knowledge_points', []):
                        if k:
                            kp_id = f"kp_{k['name']}"
                            if kp_id not in node_ids:
                                nodes.append({
                                    'id': kp_id,
                                    'label': k['name'],
                                    'type': 'knowledge',
                                    'data': {
                                        'name': k['name'],
                                        'description': k.get('theory_description', ''),
                                        'application': k.get('application_scenarios', '')
                                    }
                                })
                                node_ids.add(kp_id)

                            # 添加边
                            edges.append({
                                'id': f"{kp_id}_{kw_id}",
                                'source': kp_id,
                                'target': kw_id,
                                'type': 'has-keyword'
                            })

            return {
                'nodes': nodes,
                'edges': edges
            }
        except Exception as e:
            logger.error(f"简单查询获取节点子图失败: {e}", exc_info=True)
            raise
