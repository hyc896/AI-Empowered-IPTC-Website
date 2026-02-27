# -*- coding: utf-8 -*-
"""
基于结构化知识点数据构建知识图谱
"""
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any

# 添加GraphRAG到Python路径
graphrag_path = Path(__file__).parent.parent / "GraphRAG"
sys.path.insert(0, str(graphrag_path))

from graphrag.utils.config_loader import ConfigLoader
from graphrag.core.storage import Neo4jStorage

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    """知识图谱构建器"""

    def __init__(self, config_path: str):
        """初始化构建器"""
        logger.info("加载配置文件...")
        self.config = ConfigLoader.load_config(config_path)

        logger.info("初始化Neo4j存储...")
        self.storage = Neo4jStorage()
        self.storage.initialize(self.config['neo4j'])

        self.stats = {
            'books': 0,
            'chapters': 0,
            'sections': 0,
            'knowledge_points': 0,
            'keywords': 0,
            'relationships': 0
        }

    def load_knowledge_points(self, file_path: str) -> List[Dict[str, Any]]:
        """加载知识点数据"""
        logger.info(f"加载知识点文件: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"成功加载 {len(data)} 个知识点")
        return data

    def clear_graph(self):
        """清空现有图谱"""
        logger.info("清空现有图谱...")
        query = "MATCH (n) DETACH DELETE n"
        self.storage.execute_write(query, {})
        logger.info("图谱已清空")

    def create_book_node(self, book_id: str, book_name: str):
        """创建书籍节点"""
        query = """
        MERGE (b:Book {id: $book_id})
        ON CREATE SET b.name = $book_name, b.created_at = datetime()
        ON MATCH SET b.name = $book_name, b.updated_at = datetime()
        RETURN b
        """
        self.storage.execute_write(query, {
            'book_id': book_id,
            'book_name': book_name
        })
        self.stats['books'] += 1

    def create_chapter_node(self, book_id: str, chapter_id: str, chapter_name: str):
        """创建章节节点并关联到书籍"""
        query = """
        MATCH (b:Book {id: $book_id})
        MERGE (c:Chapter {id: $chapter_id})
        ON CREATE SET c.name = $chapter_name, c.created_at = datetime()
        ON MATCH SET c.name = $chapter_name, c.updated_at = datetime()
        MERGE (b)-[r:HAS_CHAPTER]->(c)
        RETURN c
        """
        self.storage.execute_write(query, {
            'book_id': book_id,
            'chapter_id': chapter_id,
            'chapter_name': chapter_name
        })
        self.stats['chapters'] += 1
        self.stats['relationships'] += 1

    def create_section_node(self, chapter_id: str, section_id: str, section_name: str):
        """创建节节点并关联到章节"""
        query = """
        MATCH (c:Chapter {id: $chapter_id})
        MERGE (s:Section {id: $section_id})
        ON CREATE SET s.name = $section_name, s.created_at = datetime()
        ON MATCH SET s.name = $section_name, s.updated_at = datetime()
        MERGE (c)-[r:HAS_SECTION]->(s)
        RETURN s
        """
        self.storage.execute_write(query, {
            'chapter_id': chapter_id,
            'section_id': section_id,
            'section_name': section_name
        })
        self.stats['sections'] += 1
        self.stats['relationships'] += 1

    def create_knowledge_point_node(self, kp: Dict[str, Any]):
        """创建知识点节点并关联到节"""
        query = """
        MATCH (s:Section {id: $section_id})
        MERGE (k:KnowledgePoint {name: $name})
        ON CREATE SET
            k.theory_description = $theory_description,
            k.application_scenarios = $application_scenarios,
            k.part = $part,
            k.part_num = $part_num,
            k.created_at = datetime()
        ON MATCH SET
            k.theory_description = $theory_description,
            k.application_scenarios = $application_scenarios,
            k.updated_at = datetime()
        MERGE (s)-[r:HAS_KNOWLEDGE_POINT]->(k)
        RETURN k
        """
        self.storage.execute_write(query, {
            'section_id': kp['section_id'],
            'name': kp['name'],
            'theory_description': kp.get('theory_description', ''),
            'application_scenarios': kp.get('application_scenarios', ''),
            'part': kp.get('part', ''),
            'part_num': kp.get('part_num', 0)
        })
        self.stats['knowledge_points'] += 1
        self.stats['relationships'] += 1

    def create_keywords(self, kp_name: str, keywords_str: str):
        """创建关键词节点并关联到知识点"""
        if not keywords_str:
            return

        keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
        for keyword in keywords:
            query = """
            MATCH (k:KnowledgePoint {name: $kp_name})
            MERGE (kw:Keyword {name: $keyword})
            ON CREATE SET kw.created_at = datetime()
            MERGE (k)-[r:HAS_KEYWORD]->(kw)
            RETURN kw
            """
            self.storage.execute_write(query, {
                'kp_name': kp_name,
                'keyword': keyword
            })
            self.stats['keywords'] += 1
            self.stats['relationships'] += 1

    def build_graph(self, knowledge_points: List[Dict[str, Any]]):
        """构建知识图谱"""
        logger.info("开始构建知识图谱...")

        # 收集所有唯一的书籍、章节、节
        books = {}
        chapters = {}
        sections = {}

        for kp in knowledge_points:
            book_id = kp['book_id']
            book_name = kp['book_name']
            chapter_id = kp['chapter_id']
            chapter_name = kp['chapter']
            section_id = kp['section_id']
            section_name = kp['section']

            books[book_id] = book_name
            chapters[f"{book_id}_{chapter_id}"] = (book_id, chapter_id, chapter_name)
            sections[f"{chapter_id}_{section_id}"] = (chapter_id, section_id, section_name)

        # 创建书籍节点
        logger.info(f"创建 {len(books)} 个书籍节点...")
        for book_id, book_name in books.items():
            self.create_book_node(book_id, book_name)

        # 创建章节节点
        logger.info(f"创建 {len(chapters)} 个章节节点...")
        for _, (book_id, chapter_id, chapter_name) in chapters.items():
            self.create_chapter_node(book_id, chapter_id, chapter_name)

        # 创建节节点
        logger.info(f"创建 {len(sections)} 个节节点...")
        for _, (chapter_id, section_id, section_name) in sections.items():
            self.create_section_node(chapter_id, section_id, section_name)

        # 创建知识点节点
        logger.info(f"创建 {len(knowledge_points)} 个知识点节点...")
        for i, kp in enumerate(knowledge_points, 1):
            if i % 50 == 0:
                logger.info(f"进度: {i}/{len(knowledge_points)}")
            self.create_knowledge_point_node(kp)

            # 创建关键词
            keywords_str = kp.get('typical_keywords', '')
            if keywords_str:
                self.create_keywords(kp['name'], keywords_str)

        logger.info("知识图谱构建完成！")

    def print_stats(self):
        """打印统计信息"""
        logger.info("="*80)
        logger.info("知识图谱构建统计:")
        logger.info("="*80)
        logger.info(f"书籍节点: {self.stats['books']}")
        logger.info(f"章节节点: {self.stats['chapters']}")
        logger.info(f"节节点: {self.stats['sections']}")
        logger.info(f"知识点节点: {self.stats['knowledge_points']}")
        logger.info(f"关键词节点: {self.stats['keywords']}")
        logger.info(f"关系总数: {self.stats['relationships']}")
        logger.info("="*80)

    def close(self):
        """关闭连接"""
        self.storage.close()


def main():
    """主函数"""
    # 配置文件路径
    config_path = Path(__file__).parent.parent / "GraphRAG" / "config" / "default_config.yaml"

    # 知识点文件路径
    knowledge_points_path = Path(__file__).parent.parent.parent / "data" / "knowledge_points.json"

    logger.info("="*80)
    logger.info("开始构建思政课知识图谱")
    logger.info("="*80)
    logger.info(f"配置文件: {config_path}")
    logger.info(f"知识点文件: {knowledge_points_path}")
    logger.info("="*80)

    # 检查文件是否存在
    if not config_path.exists():
        logger.error(f"配置文件不存在: {config_path}")
        return

    if not knowledge_points_path.exists():
        logger.error(f"知识点文件不存在: {knowledge_points_path}")
        return

    # 创建构建器
    builder = None
    try:
        builder = KnowledgeGraphBuilder(str(config_path))

        # 加载知识点数据
        knowledge_points = builder.load_knowledge_points(str(knowledge_points_path))

        # 清空现有图谱
        builder.clear_graph()

        # 构建图谱
        builder.build_graph(knowledge_points)

        # 打印统计信息
        builder.print_stats()

    except Exception as e:
        logger.error(f"构建失败: {e}", exc_info=True)

    finally:
        if builder:
            builder.close()


if __name__ == "__main__":
    main()

