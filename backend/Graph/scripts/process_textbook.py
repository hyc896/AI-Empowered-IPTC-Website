# -*- coding: utf-8 -*-
"""
从教材JSON文件中提取实体和关系，构建知识图谱

使用GraphRAG工具包处理思政课教材，提取理论、政策、人物、事件等实体，
以及它们之间的关系，存储到Neo4j数据库中。
"""

import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any

# 添加GraphRAG到Python路径
graphrag_path = Path(__file__).parent.parent / "GraphRAG"
sys.path.insert(0, str(graphrag_path))

from graphrag.utils.config_loader import ConfigLoader
from graphrag.llm.openai_client import OpenAIClient
from graphrag.core.entity_extractor import EntityExtractorService
from graphrag.core.storage import Neo4jStorage

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TextbookProcessor:
    """教材处理器"""

    def __init__(self, config_path: str):
        """初始化处理器

        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        logger.info(f"加载配置文件: {config_path}")
        self.config = ConfigLoader.load_config(config_path)

        # 验证配置
        if not ConfigLoader.validate_config(self.config):
            raise ValueError("配置验证失败")

        # 初始化LLM客户端
        llm_config = self.config['llm']
        logger.info(f"初始化LLM客户端: {llm_config['model']}")
        self.llm_client = OpenAIClient(
            api_key=llm_config['api_key'],
            model=llm_config['model'],
            base_url=llm_config.get('base_url')
        )

        # 初始化实体提取服务
        max_chunk_chars = self.config.get('entity_extraction', {}).get('max_chunk_chars', 20000)
        logger.info(f"初始化实体提取服务，最大块大小: {max_chunk_chars}")
        self.entity_extractor = EntityExtractorService(
            llm_manager=self.llm_client,
            max_chunk_chars=max_chunk_chars
        )

        # 初始化Neo4j存储
        logger.info("初始化Neo4j存储")
        self.storage = Neo4jStorage()
        self.storage.initialize(self.config['neo4j'])

        # 统计信息
        self.stats = {
            'total_chapters': 0,
            'total_sections': 0,
            'total_entities': 0,
            'total_relations': 0,
            'failed_sections': []
        }

    def load_textbook(self, textbook_path: str) -> List[Dict]:
        """加载教材JSON文件

        Args:
            textbook_path: 教材JSON文件路径

        Returns:
            章节列表
        """
        logger.info(f"加载教材文件: {textbook_path}")
        with open(textbook_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        chapters = data.get('chapters', [])
        logger.info(f"成功加载 {len(chapters)} 个章节")
        return chapters

    async def process_section(self, chapter_id: str, section: Dict) -> Dict[str, Any]:
        """处理单个章节

        Args:
            chapter_id: 章节ID
            section: 章节数据

        Returns:
            提取结果
        """
        section_id = section.get('section_id', 'unknown')
        section_name = section.get('section_name', '未命名章节')
        text = section.get('text', '')

        logger.info(f"处理章节: {chapter_id} - {section_id} - {section_name}")
        logger.info(f"文本长度: {len(text)} 字符")

        if not text or len(text.strip()) < 50:
            logger.warning(f"章节文本过短，跳过: {section_id}")
            return {"entities": [], "relations": []}

        try:
            # 提取实体和关系
            result = await self.entity_extractor.extract_entities(
                text=text,
                language="zh"
            )

            entities_count = len(result.get('entities', []))
            relations_count = len(result.get('relations', []))

            logger.info(f"提取完成: {entities_count} 个实体, {relations_count} 个关系")

            # 更新统计
            self.stats['total_entities'] += entities_count
            self.stats['total_relations'] += relations_count

            return result

        except Exception as e:
            logger.error(f"处理章节失败 {section_id}: {e}", exc_info=True)
            self.stats['failed_sections'].append({
                'chapter_id': chapter_id,
                'section_id': section_id,
                'section_name': section_name,
                'error': str(e)
            })
            return {"entities": [], "relations": []}

    def store_entities(self, entities: List[Dict]) -> int:
        """存储实体到Neo4j

        Args:
            entities: 实体列表

        Returns:
            存储的实体数量
        """
        if not entities:
            return 0

        stored_count = 0
        for entity in entities:
            try:
                # 构建Cypher查询
                query = """
                MERGE (e:Entity {name: $name, type: $type})
                ON CREATE SET
                    e.aliases = $aliases,
                    e.attributes = $attributes,
                    e.created_at = datetime()
                ON MATCH SET
                    e.aliases = $aliases,
                    e.attributes = $attributes,
                    e.updated_at = datetime()
                RETURN e
                """

                parameters = {
                    'name': entity.get('name'),
                    'type': entity.get('type'),
                    'aliases': entity.get('aliases', []),
                    'attributes': json.dumps(entity.get('attributes', {}), ensure_ascii=False)
                }

                self.storage.execute_write(query, parameters)
                stored_count += 1

            except Exception as e:
                logger.error(f"存储实体失败 {entity.get('name')}: {e}")

        return stored_count

    def store_relations(self, relations: List[Dict]) -> int:
        """存储关系到Neo4j

        Args:
            relations: 关系列表

        Returns:
            存储的关系数量
        """
        if not relations:
            return 0

        stored_count = 0
        for relation in relations:
            try:
                # 构建Cypher查询
                query = """
                MATCH (source:Entity {name: $source_name})
                MATCH (target:Entity {name: $target_name})
                MERGE (source)-[r:%s]->(target)
                ON CREATE SET
                    r.properties = $properties,
                    r.created_at = datetime()
                ON MATCH SET
                    r.properties = $properties,
                    r.updated_at = datetime()
                RETURN r
                """ % relation.get('type', 'RELATED_TO')

                parameters = {
                    'source_name': relation.get('source'),
                    'target_name': relation.get('target'),
                    'properties': json.dumps(relation.get('properties', {}), ensure_ascii=False)
                }

                self.storage.execute_write(query, parameters)
                stored_count += 1

            except Exception as e:
                logger.error(f"存储关系失败 {relation.get('source')} -> {relation.get('target')}: {e}")

        return stored_count

    async def process_textbook(self, textbook_path: str):
        """处理整本教材

        Args:
            textbook_path: 教材JSON文件路径
        """
        # 加载教材
        chapters = self.load_textbook(textbook_path)
        self.stats['total_chapters'] = len(chapters)

        # 处理每个章节
        for chapter in chapters:
            chapter_id = chapter.get('chapter_id', 'unknown')
            chapter_name = chapter.get('chapter_name', '未命名章节')
            sections = chapter.get('sections', [])

            logger.info(f"\n{'='*80}")
            logger.info(f"处理章节: {chapter_id} - {chapter_name}")
            logger.info(f"包含 {len(sections)} 个小节")
            logger.info(f"{'='*80}\n")

            self.stats['total_sections'] += len(sections)

            # 处理每个小节
            for section in sections:
                # 提取实体和关系
                result = await self.process_section(chapter_id, section)

                # 存储到Neo4j
                if result.get('entities'):
                    entities_stored = self.store_entities(result['entities'])
                    logger.info(f"存储了 {entities_stored} 个实体")

                if result.get('relations'):
                    relations_stored = self.store_relations(result['relations'])
                    logger.info(f"存储了 {relations_stored} 个关系")

        # 打印统计信息
        self.print_statistics()

    def print_statistics(self):
        """打印统计信息"""
        logger.info(f"\n{'='*80}")
        logger.info("处理完成！统计信息：")
        logger.info(f"{'='*80}")
        logger.info(f"总章节数: {self.stats['total_chapters']}")
        logger.info(f"总小节数: {self.stats['total_sections']}")
        logger.info(f"提取实体数: {self.stats['total_entities']}")
        logger.info(f"提取关系数: {self.stats['total_relations']}")
        logger.info(f"失败小节数: {len(self.stats['failed_sections'])}")

        if self.stats['failed_sections']:
            logger.warning(f"\n失败的小节:")
            for failed in self.stats['failed_sections']:
                logger.warning(f"  - {failed['chapter_id']} / {failed['section_id']}: {failed['error']}")

        logger.info(f"{'='*80}\n")

    def close(self):
        """关闭连接"""
        logger.info("关闭Neo4j连接")
        self.storage.close()


async def main():
    """主函数"""
    # 配置文件路径
    config_path = Path(__file__).parent.parent / "GraphRAG" / "config" / "default_config.yaml"

    # 教材文件路径（先处理习近平思想概论）
    textbook_path = Path(__file__).parent.parent / "data" / "xi_thought_2023_chapters.json"

    logger.info("="*80)
    logger.info("开始处理思政课教材，构建知识图谱")
    logger.info("="*80)
    logger.info(f"配置文件: {config_path}")
    logger.info(f"教材文件: {textbook_path}")
    logger.info("="*80)

    # 检查文件是否存在
    if not config_path.exists():
        logger.error(f"配置文件不存在: {config_path}")
        return

    if not textbook_path.exists():
        logger.error(f"教材文件不存在: {textbook_path}")
        return

    # 创建处理器
    processor = None
    try:
        processor = TextbookProcessor(str(config_path))

        # 处理教材
        await processor.process_textbook(str(textbook_path))

    except Exception as e:
        logger.error(f"处理失败: {e}", exc_info=True)

    finally:
        if processor:
            processor.close()


if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())

