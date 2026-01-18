"""
GraphRAG 服务封装
负责封装 GraphRAG 工具包的核心功能
"""
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加 GraphRAG 到 Python 路径
graphrag_path = Path(__file__).parent.parent.parent.parent / "GraphRAG"
sys.path.insert(0, str(graphrag_path))

from graphrag.utils.config_loader import ConfigLoader
from graphrag.core.storage import Neo4jStorage
from graphrag.core.entity_extractor import EntityExtractorService
from graphrag.core.graph_builder import GraphBuilderService
from graphrag.llm.openai_client import OpenAIClient


class GraphRAGService:
    """GraphRAG 服务单例类"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化服务（仅执行一次）"""
        if not GraphRAGService._initialized:
            self.storage = None
            self.extractor = None
            self.builder = None
            self.config = None
            GraphRAGService._initialized = True

    async def initialize(self, config_path: str):
        """
        初始化 GraphRAG 组件

        Args:
            config_path: 配置文件路径
        """
        if self.storage is not None:
            return  # 已初始化

        # 加载配置
        self.config = ConfigLoader.load_config(config_path)

        # 初始化 Neo4j 存储
        self.storage = Neo4jStorage()
        self.storage.initialize(self.config['neo4j'])

        # 初始化 LLM 客户端
        llm_client = OpenAIClient(
            api_key=self.config['llm']['api_key'],
            model=self.config['llm']['model']
        )

        # 初始化实体提取器
        self.extractor = EntityExtractorService(
            llm_client,
            max_chunk_chars=self.config.get('entity_extraction', {}).get('max_chunk_chars', 20000)
        )

        # 初始化图谱构建器
        self.builder = GraphBuilderService(self.storage)

    async def extract_entities(self, text: str, language: str = "zh") -> Dict[str, Any]:
        """
        提取实体和关系

        Args:
            text: 待提取的文本
            language: 语言（zh 或 en）

        Returns:
            包含 entities 和 relations 的字典
        """
        if self.extractor is None:
            raise RuntimeError("GraphRAG 服务未初始化")

        result = await self.extractor.extract_entities(text, language)
        return result

    async def build_graph(
        self,
        file_id: str,
        filename: str,
        page_range: str,
        entities: List[Dict],
        relations: List[Dict]
    ) -> Dict[str, int]:
        """
        构建知识图谱

        Args:
            file_id: 文件 ID
            filename: 文件名
            page_range: 页面范围
            entities: 实体列表
            relations: 关系列表

        Returns:
            统计信息
        """
        if self.builder is None:
            raise RuntimeError("GraphRAG 服务未初始化")

        # 构建消息数据
        message_data = {
            "source_id": file_id,
            "source_name": "PDF Upload",
            "title": f"{filename} ({page_range})",
            "summary": f"从 {filename} 的第 {page_range} 页提取",
            "url": f"file://{file_id}",
            "published_at": "",
            "crawled_at": ""
        }

        stats = await self.builder.add_message_with_entities(
            message_id=f"{file_id}_{page_range}",
            message_data=message_data,
            entities=entities,
            relations=relations
        )

        return stats

    async def get_graph_data(self, file_id: str, page_range: Optional[str] = None) -> Dict[str, Any]:
        """
        获取图谱可视化数据

        Args:
            file_id: 文件 ID
            page_range: 页面范围（可选）

        Returns:
            ECharts 格式的图谱数据
        """
        if self.storage is None:
            raise RuntimeError("GraphRAG 服务未初始化")

        # 构建查询条件
        message_id = f"{file_id}_{page_range}" if page_range else file_id

        # 查询实体和关系
        query = """
        MATCH (m:Message {id: $message_id})-[:MENTIONS]->(e:Entity)
        OPTIONAL MATCH (e)-[r]->(e2:Entity)
        RETURN e, r, e2
        """

        results = await self.storage.execute_read_async(query, {"message_id": message_id})

        # 转换为 ECharts 格式
        nodes = []
        links = []
        node_ids = set()

        for record in results:
            entity = record.get('e')
            if entity and entity['name'] not in node_ids:
                nodes.append({
                    "id": entity['name'],
                    "name": entity['name'],
                    "category": entity['type'],
                    "value": entity.get('mention_count', 1),
                    "symbolSize": min(30 + entity.get('mention_count', 1) * 5, 80)
                })
                node_ids.add(entity['name'])

            relation = record.get('r')
            entity2 = record.get('e2')
            if relation and entity2:
                if entity2['name'] not in node_ids:
                    nodes.append({
                        "id": entity2['name'],
                        "name": entity2['name'],
                        "category": entity2['type'],
                        "value": entity2.get('mention_count', 1),
                        "symbolSize": min(30 + entity2.get('mention_count', 1) * 5, 80)
                    })
                    node_ids.add(entity2['name'])

                links.append({
                    "source": entity['name'],
                    "target": entity2['name'],
                    "value": 1,
                    "label": relation.type
                })

        # 获取所有实体类型
        categories = list(set([node['category'] for node in nodes]))
        categories_list = [{"name": cat} for cat in categories]

        return {
            "nodes": nodes,
            "links": links,
            "categories": categories_list
        }

    async def close(self):
        """关闭连接"""
        if self.storage:
            self.storage.close()
