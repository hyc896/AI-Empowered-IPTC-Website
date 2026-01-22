"""
GraphRAG 服务封装
负责封装 GraphRAG 工具包的核心功能
"""
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from slugify import slugify

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
            model=self.config['llm']['model'],
            base_url=self.config['llm'].get('base_url')
        )

        # 初始化实体提取器
        self.extractor = EntityExtractorService(
            llm_client,
            max_chunk_chars=self.config.get('entity_extraction', {}).get('max_chunk_chars', 20000)
        )

        # 初始化图谱构建器
        self.builder = GraphBuilderService(self.storage)

    async def extract_entities(self, text: str, language: str = "zh", file_id: str = None, progress_manager = None) -> Dict[str, Any]:
        """
        提取实体和关系

        Args:
            text: 待提取的文本
            language: 语言（zh 或 en）
            file_id: 文件ID(用于进度更新)
            progress_manager: 进度管理器(可选)

        Returns:
            包含 entities 和 relations 的字典
        """
        if self.extractor is None:
            raise RuntimeError("GraphRAG 服务未初始化")

        print(f"📝 开始提取实体，文本长度: {len(text)}")
        result = await self.extractor.extract_entities(text, language, file_id, progress_manager)
        print(f"✅ 实体提取完成，结果: entities={len(result.get('entities', []))}, relations={len(result.get('relations', []))}")
        return result

    async def process_text(
        self,
        text: str,
        file_id: str,
        filename: str,
        page_range: str = "1-全文",
        progress_manager = None
    ) -> Dict[str, Any]:
        """
        处理文本：提取实体并构建图谱

        Args:
            text: 待处理的文本
            file_id: 文件 ID
            filename: 文件名
            page_range: 页面范围
            progress_manager: 进度管理器(可选)

        Returns:
            处理结果统计
        """
        print(f"🔄 开始处理文件: {filename}")

        # 更新进度: 开始提取实体
        if progress_manager:
            await progress_manager.set_progress(
                file_id=file_id,
                status="processing",
                progress=20,
                message="正在提取实体..."
            )

        # 提取实体
        result = await self.extract_entities(text, file_id, progress_manager)
        entities = result.get('entities', [])
        relations = result.get('relations', [])

        print(f"📊 提取到 {len(entities)} 个实体, {len(relations)} 个关系")

        # 更新进度: 实体提取完成
        if progress_manager:
            await progress_manager.set_progress(
                file_id=file_id,
                status="processing",
                progress=80,
                message=f"实体提取完成,正在构建图谱...",
                entities_count=len(entities),
                relations_count=len(relations)
            )

        # 为每个实体添加页码信息
        for entity in entities:
            entity['page_range'] = page_range

        # 构建图谱
        stats = await self.build_graph(file_id, filename, page_range, entities, relations)

        print(f"✅ 图谱构建完成: {stats}")

        # 更新进度: 图谱构建完成
        if progress_manager:
            await progress_manager.set_progress(
                file_id=file_id,
                status="processing",
                progress=95,
                message="图谱构建完成",
                entities_count=len(entities),
                relations_count=len(relations)
            )

        return stats

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
            "name": filename,
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

        # 先查询所有相关的 Message 节点
        check_query = """
        MATCH (m:Message)
        WHERE m.id STARTS WITH $file_id
        RETURN m.id as message_id
        LIMIT 10
        """

        check_results = await self.storage.execute_read_async(check_query, {"file_id": file_id})
        print(f"找到的 Message 节点: {[r['message_id'] for r in check_results]}")

        # 如果没有找到精确匹配，使用第一个匹配的
        if check_results:
            message_id = check_results[0]['message_id']
        else:
            message_id = f"{file_id}_{page_range}" if page_range else file_id

        print(f"使用的 message_id: {message_id}")

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
            if entity:
                entity_dict = dict(entity) if hasattr(entity, '__iter__') and not isinstance(entity, str) else entity
                entity_name = entity_dict.get('name') if isinstance(entity_dict, dict) else str(entity)
                entity_type = entity_dict.get('type', 'unknown') if isinstance(entity_dict, dict) else 'unknown'

                if entity_name not in node_ids:
                    nodes.append({
                        "id": entity_name,
                        "name": entity_name,
                        "category": entity_type,
                        "value": entity_dict.get('mention_count', 1) if isinstance(entity_dict, dict) else 1,
                        "symbolSize": min(30 + (entity_dict.get('mention_count', 1) if isinstance(entity_dict, dict) else 1) * 5, 80)
                    })
                    node_ids.add(entity_name)

            relation = record.get('r')
            entity2 = record.get('e2')
            if relation and entity2:
                entity2_dict = dict(entity2) if hasattr(entity2, '__iter__') and not isinstance(entity2, str) else entity2
                entity2_name = entity2_dict.get('name') if isinstance(entity2_dict, dict) else str(entity2)
                entity2_type = entity2_dict.get('type', 'unknown') if isinstance(entity2_dict, dict) else 'unknown'

                if entity2_name not in node_ids:
                    nodes.append({
                        "id": entity2_name,
                        "name": entity2_name,
                        "category": entity2_type,
                        "value": entity2_dict.get('mention_count', 1) if isinstance(entity2_dict, dict) else 1,
                        "symbolSize": min(30 + (entity2_dict.get('mention_count', 1) if isinstance(entity2_dict, dict) else 1) * 5, 80)
                    })
                    node_ids.add(entity2_name)

                relation_type = relation.type if hasattr(relation, 'type') else (relation[1] if isinstance(relation, tuple) and len(relation) > 1 else 'RELATED_TO')

                links.append({
                    "source": entity_name,
                    "target": entity2_name,
                    "value": 1,
                    "label": relation_type
                })

        # 获取所有实体类型
        categories = list(set([node['category'] for node in nodes]))
        categories_list = [{"name": cat} for cat in categories]

        return {
            "nodes": nodes,
            "links": links,
            "categories": categories_list
        }

    async def get_cosma_data(self, file_id: str) -> Dict[str, Any]:
        """
        转换 Neo4j 数据为 Cosma Records 格式

        Args:
            file_id: 文件 ID

        Returns:
            Cosma Records 格式的数据
        """
        # 查找匹配的 Message 节点
        find_query = """
        MATCH (m:Message)
        WHERE m.id STARTS WITH $file_id
        RETURN m.id as message_id
        LIMIT 1
        """

        check_results = await self.storage.execute_read_async(find_query, {"file_id": file_id})

        if not check_results:
            message_id = file_id
        else:
            message_id = check_results[0]['message_id']

        # 查询实体和关系
        query = """
        MATCH (m:Message {id: $message_id})-[:MENTIONS]->(e:Entity)
        OPTIONAL MATCH (e)-[r]->(e2:Entity)
        RETURN e, collect({type: type(r), target: e2.name}) as outgoing_links
        """

        results = await self.storage.execute_read_async(query, {"message_id": message_id})

        # 转换为 Cosma Records,使用字典去重
        records_dict = {}
        for record in results:
            entity = record.get('e')
            if not entity:
                continue

            entity_dict = dict(entity) if hasattr(entity, '__iter__') and not isinstance(entity, str) else entity
            entity_name = entity_dict.get('name') if isinstance(entity_dict, dict) else str(entity)
            entity_type = entity_dict.get('type', 'unknown') if isinstance(entity_dict, dict) else 'unknown'
            mention_count = entity_dict.get('mention_count', 1) if isinstance(entity_dict, dict) else 1

            # 生成 slugified ID
            entity_id = slugify(entity_name)

            # 构建链接列表
            links = []
            outgoing_links = record.get('outgoing_links', [])
            for link in outgoing_links:
                if link and link.get('target'):
                    links.append({
                        'type': link.get('type', 'RELATED_TO'),
                        'target': slugify(link['target']),
                        'target_name': link['target'],
                        'contexts': []
                    })

            # 获取页码范围信息
            page_range = entity_dict.get('page_range', '') if isinstance(entity_dict, dict) else ''

            # 如果实体 ID 已存在,合并信息
            if entity_id in records_dict:
                existing = records_dict[entity_id]
                # 合并链接(去重)
                existing_link_keys = {(l['type'], l['target']) for l in existing['links']}
                for link in links:
                    link_key = (link['type'], link['target'])
                    if link_key not in existing_link_keys:
                        existing['links'].append(link)
                        existing_link_keys.add(link_key)
                # 累加提及次数
                existing['metas']['mention_count'] += mention_count
                # 更新内容
                existing['content'] = f"# {entity_name}\n\n**类型**: {entity_type}\n\n**提及次数**: {existing['metas']['mention_count']}"
                if page_range:
                    existing['content'] += f"\n\n**出现页码**: {page_range}"
            else:
                # 生成 Markdown 内容
                content = f"# {entity_name}\n\n**类型**: {entity_type}\n\n**提及次数**: {mention_count}"
                if page_range:
                    content += f"\n\n**出现页码**: {page_range}"

                records_dict[entity_id] = {
                    'id': entity_id,
                    'title': entity_name,
                    'content': content,
                    'links': links,
                    'types': [entity_type],
                    'tags': [],
                    'metas': {
                        'mention_count': mention_count,
                        'page_range': page_range
                    }
                }

        # 转换字典为列表
        records = list(records_dict.values())
        return {'records': records}

    async def save_books_to_neo4j(self, entity_name: str, books: List[Dict[str, Any]]) -> bool:
        """
        保存图书信息到 Neo4j

        Args:
            entity_name: 实体名称（搜索关键词）
            books: 图书列表

        Returns:
            是否保存成功
        """
        if not self.storage:
            return False

        try:
            for book in books:
                # 创建 Book 节点，使用 keyword 作为关联键
                query = """
                MERGE (b:Book {title: $title})
                SET b.author = $author,
                    b.cover = $cover,
                    b.link = $link,
                    b.publisher = $publisher,
                    b.isbn = $isbn,
                    b.description = $description,
                    b.keyword = $keyword,
                    b.updated_at = datetime()
                """

                self.storage.driver.execute_query(
                    query,
                    title=book.get('title', ''),
                    author=book.get('author', ''),
                    cover=book.get('cover', ''),
                    link=book.get('link', ''),
                    publisher=book.get('publisher', ''),
                    isbn=book.get('isbn', ''),
                    description=book.get('description', ''),
                    keyword=entity_name
                )

            return True
        except Exception as e:
            print(f"保存图书到 Neo4j 失败: {str(e)}")
            return False

    async def get_books_from_neo4j(self, entity_name: str) -> List[Dict[str, Any]]:
        """
        从 Neo4j 获取关键词关联的图书信息

        Args:
            entity_name: 搜索关键词

        Returns:
            图书列表
        """
        if not self.storage:
            return []

        try:
            query = """
            MATCH (b:Book {keyword: $keyword})
            RETURN b.title as title,
                   b.author as author,
                   b.cover as cover,
                   b.link as link,
                   b.publisher as publisher,
                   b.isbn as isbn,
                   b.description as description
            ORDER BY b.updated_at DESC
            """

            records, _, _ = self.storage.driver.execute_query(
                query,
                keyword=entity_name
            )

            books = []
            for record in records:
                books.append({
                    'title': record['title'],
                    'author': record['author'],
                    'cover': record['cover'],
                    'link': record['link'],
                    'publisher': record.get('publisher', ''),
                    'isbn': record.get('isbn', ''),
                    'description': record.get('description', '')
                })

            return books
        except Exception as e:
            print(f"从 Neo4j 获取图书失败: {str(e)}")
            return []

    async def close(self):
        """关闭连接"""
        if self.storage:
            self.storage.close()


# 创建全局单例实例
graphrag_service = GraphRAGService()
