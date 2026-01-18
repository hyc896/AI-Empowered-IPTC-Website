"""
GraphRAG - 独立的知识图谱构建工具包

本工具包提供知识图谱构建、实体提取、关系推理等核心功能。
可被message_platform或其他项目调用。

主要功能：
- Neo4j图数据库存储
- LLM驱动的实体提取
- 图谱构建和查询
- 多种LLM提供商支持

使用示例：
    from graphrag import GraphRAG

    rag = GraphRAG(config_path="config/default_config.yaml")
    await rag.initialize()

    result = await rag.extract_entities(text)
    await rag.build_graph(doc_id, doc_data, result['entities'], result['relations'])

    await rag.close()
"""

__version__ = "0.1.0"

# 核心类将在后续实现后导出
# from .graphrag import GraphRAG
# __all__ = ['GraphRAG']
