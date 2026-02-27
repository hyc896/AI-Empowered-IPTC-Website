"""
基础使用示例

演示GraphRAG工具包的基本功能：
- 初始化GraphRAG
- 提取实体和关系
- 构建知识图谱
- 查询实体
"""

import asyncio
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from graphrag.core.storage import Neo4jStorage
from graphrag.core.entity_extractor import EntityExtractor
from graphrag.core.graph_builder import GraphBuilder
from graphrag.llm.openai_client import OpenAIClient
from graphrag.utils.config_loader import ConfigLoader


async def main():
    # 加载配置
    config_path = Path(__file__).parent.parent / "config" / "default_config.yaml"
    config = ConfigLoader.load_config(str(config_path))

    # 初始化Neo4j存储
    storage = Neo4jStorage()
    storage.initialize(config['neo4j'])
    print("Neo4j连接成功")

    # 初始化LLM客户端
    llm_config = config['llm']
    llm_client = OpenAIClient(
        api_key=llm_config['api_key'],
        model=llm_config['model']
    )
    print(f"LLM客户端初始化成功: {llm_config['model']}")

    # 初始化实体提取器
    extractor = EntityExtractor(llm_client)

    # 初始化图谱构建器
    builder = GraphBuilder(storage)

    # 待处理的文本
    text = """
    OpenAI发布了GPT-4模型，这是一个强大的大语言模型。
    Sam Altman是OpenAI的CEO，他领导公司开发了ChatGPT产品。
    微软投资了OpenAI，双方建立了战略合作关系。
    """

    print("\n开始提取实体和关系...")
    # 提取实体和关系
    result = await extractor.extract_entities(text)
    print(f"提取到 {len(result['entities'])} 个实体")
    print(f"提取到 {len(result['relations'])} 个关系")

    # 打印实体
    print("\n实体列表:")
    for entity in result['entities']:
        print(f"  - {entity['name']} ({entity['type']})")

    # 打印关系
    print("\n关系列表:")
    for relation in result['relations']:
        print(f"  - {relation['source']} --[{relation['type']}]--> {relation['target']}")

    # 构建图谱
    print("\n开始构建图谱...")
    doc_data = {
        "title": "OpenAI新闻",
        "content": text,
        "url": "https://example.com/news/1",
        "published_at": "2025-01-01T00:00:00",
        "crawled_at": "2025-01-01T00:00:00"
    }

    stats = await builder.add_document_with_entities(
        doc_id="doc_001",
        doc_data=doc_data,
        entities=result['entities'],
        relations=result['relations']
    )

    print(f"图谱构建完成:")
    print(f"  - 创建文档: {stats.get('document_created', 0)}")
    print(f"  - 创建实体: {stats.get('entities_created', 0)}")
    print(f"  - 创建提及关系: {stats.get('mentions_created', 0)}")
    print(f"  - 创建实体关系: {stats.get('relations_created', 0)}")

    # 查询实体
    print("\n查询实体 'OpenAI'...")
    query = """
    MATCH (e:Entity {name: 'OpenAI'})
    RETURN e.name as name, e.type as type, e.mention_count as mention_count
    """
    entities = await storage.execute_read_async(query)
    if entities:
        entity = entities[0]
        print(f"找到实体: {entity['name']} ({entity['type']})")
        print(f"提及次数: {entity['mention_count']}")

    # 关闭连接
    storage.close()
    print("\n完成！")


if __name__ == "__main__":
    asyncio.run(main())
