# -*- coding: utf-8 -*-
"""
导出知识图谱数据
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


class KnowledgeGraphExporter:
    """知识图谱导出器"""

    def __init__(self, config_path: str):
        """初始化导出器"""
        logger.info("加载配置文件...")
        self.config = ConfigLoader.load_config(config_path)

        logger.info("初始化Neo4j存储...")
        self.storage = Neo4jStorage()
        self.storage.initialize(self.config['neo4j'])

    def export_nodes(self) -> Dict[str, List[Dict]]:
        """导出所有节点"""
        logger.info("导出节点数据...")

        nodes = {
            'books': [],
            'chapters': [],
            'sections': [],
            'knowledge_points': [],
            'keywords': []
        }

        # 导出书籍节点
        query = "MATCH (b:Book) RETURN b.id as id, b.name as name"
        results = self.storage.execute_read(query)
        for record in results:
            nodes['books'].append({
                'id': record['id'],
                'name': record['name']
            })
        logger.info(f"导出 {len(nodes['books'])} 个书籍节点")

        # 导出章节节点
        query = "MATCH (c:Chapter) RETURN c.id as id, c.name as name"
        results = self.storage.execute_read(query)
        for record in results:
            nodes['chapters'].append({
                'id': record['id'],
                'name': record['name']
            })
        logger.info(f"导出 {len(nodes['chapters'])} 个章节节点")

        # 导出节节点
        query = "MATCH (s:Section) RETURN s.id as id, s.name as name"
        results = self.storage.execute_read(query)
        for record in results:
            nodes['sections'].append({
                'id': record['id'],
                'name': record['name']
            })
        logger.info(f"导出 {len(nodes['sections'])} 个节节点")

        # 导出知识点节点
        query = """
        MATCH (k:KnowledgePoint)
        RETURN k.name as name, k.theory_description as theory_description,
               k.application_scenarios as application_scenarios,
               k.part as part, k.part_num as part_num
        """
        results = self.storage.execute_read(query)
        for record in results:
            nodes['knowledge_points'].append({
                'name': record['name'],
                'theory_description': record.get('theory_description', ''),
                'application_scenarios': record.get('application_scenarios', ''),
                'part': record.get('part', ''),
                'part_num': record.get('part_num', 0)
            })
        logger.info(f"导出 {len(nodes['knowledge_points'])} 个知识点节点")

        # 导出关键词节点
        query = "MATCH (kw:Keyword) RETURN kw.name as name"
        results = self.storage.execute_read(query)
        for record in results:
            nodes['keywords'].append({
                'name': record['name']
            })
        logger.info(f"导出 {len(nodes['keywords'])} 个关键词节点")

        return nodes

    def export_relationships(self) -> List[Dict]:
        """导出所有关系"""
        logger.info("导出关系数据...")

        relationships = []

        # 导出所有关系
        query = """
        MATCH (a)-[r]->(b)
        RETURN
            labels(a)[0] as source_type,
            CASE
                WHEN 'Book' IN labels(a) THEN a.id
                WHEN 'Chapter' IN labels(a) THEN a.id
                WHEN 'Section' IN labels(a) THEN a.id
                WHEN 'KnowledgePoint' IN labels(a) THEN a.name
                WHEN 'Keyword' IN labels(a) THEN a.name
            END as source_id,
            type(r) as relationship_type,
            labels(b)[0] as target_type,
            CASE
                WHEN 'Book' IN labels(b) THEN b.id
                WHEN 'Chapter' IN labels(b) THEN b.id
                WHEN 'Section' IN labels(b) THEN b.id
                WHEN 'KnowledgePoint' IN labels(b) THEN b.name
                WHEN 'Keyword' IN labels(b) THEN b.name
            END as target_id
        """
        results = self.storage.execute_read(query)
        for record in results:
            relationships.append({
                'source_type': record['source_type'],
                'source_id': record['source_id'],
                'relationship_type': record['relationship_type'],
                'target_type': record['target_type'],
                'target_id': record['target_id']
            })

        logger.info(f"导出 {len(relationships)} 个关系")
        return relationships

    def export_to_json(self, output_path: str):
        """导出为JSON文件"""
        logger.info("开始导出知识图谱...")

        # 导出节点
        nodes = self.export_nodes()

        # 导出关系
        relationships = self.export_relationships()

        # 组装数据
        data = {
            'nodes': nodes,
            'relationships': relationships,
            'statistics': {
                'books': len(nodes['books']),
                'chapters': len(nodes['chapters']),
                'sections': len(nodes['sections']),
                'knowledge_points': len(nodes['knowledge_points']),
                'keywords': len(nodes['keywords']),
                'relationships': len(relationships)
            }
        }

        # 保存到文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"知识图谱已导出到: {output_path}")
        return data

    def close(self):
        """关闭连接"""
        self.storage.close()


def main():
    """主函数"""
    config_path = Path(__file__).parent.parent / "GraphRAG" / "config" / "default_config.yaml"
    output_path = Path(__file__).parent.parent / "data" / "knowledge_graph_export.json"

    logger.info("="*80)
    logger.info("知识图谱导出工具")
    logger.info("="*80)

    exporter = None
    try:
        exporter = KnowledgeGraphExporter(str(config_path))
        data = exporter.export_to_json(str(output_path))

        logger.info("="*80)
        logger.info("导出完成！统计信息:")
        logger.info(f"书籍: {data['statistics']['books']}")
        logger.info(f"章节: {data['statistics']['chapters']}")
        logger.info(f"节: {data['statistics']['sections']}")
        logger.info(f"知识点: {data['statistics']['knowledge_points']}")
        logger.info(f"关键词: {data['statistics']['keywords']}")
        logger.info(f"关系: {data['statistics']['relationships']}")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"导出失败: {e}", exc_info=True)

    finally:
        if exporter:
            exporter.close()


if __name__ == "__main__":
    main()

