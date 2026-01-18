# GraphRAG - 独立的知识图谱构建工具包

GraphRAG是一个独立的Python工具包，提供知识图谱构建、实体提取、关系推理等核心功能。可被message_platform或其他项目调用。

## 主要功能

- **Neo4j图数据库存储**：高性能的图数据存储和查询
- **LLM驱动的实体提取**：支持8种实体类型和7种关系类型
- **图谱构建和查询**：自动去重、关系推理、多跳查询
- **多种LLM提供商支持**：OpenAI、Anthropic、自定义LLM

## 快速开始

### 安装

```bash
# 从源码安装
cd GraphRAG
pip install -e .

# 或安装所有可选依赖
pip install -e ".[all]"
```

### 基础使用

```python
import asyncio
from graphrag import GraphRAG

async def main():
    # 初始化GraphRAG
    rag = GraphRAG(config_path="config/default_config.yaml")
    await rag.initialize()

    # 待处理的文本
    text = """
    OpenAI发布了GPT-4模型，这是一个强大的大语言模型。
    Sam Altman是OpenAI的CEO。
    """

    # 提取实体和关系
    result = await rag.extract_entities(text)

    # 构建图谱
    doc_data = {
        "title": "OpenAI新闻",
        "content": text,
        "url": "https://example.com/news/1",
        "published_at": "2025-01-01T00:00:00"
    }

    stats = await rag.build_graph(
        doc_id="doc_001",
        doc_data=doc_data,
        entities=result['entities'],
        relations=result['relations']
    )

    # 查询实体
    entities = await rag.search_entities("OpenAI")

    # 关闭连接
    await rag.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## 配置

在`config/default_config.yaml`中配置Neo4j和LLM：

```yaml
neo4j:
  uri: bolt://localhost:7687
  user: neo4j
  password: your_password

llm:
  provider: openai
  model: gpt-4
  api_key: your_api_key
```

支持环境变量：

```bash
export NEO4J_PASSWORD=your_password
export LLM_API_KEY=your_api_key
```

## 文档

- [工具包说明](docs/工具包说明.md) - 完整的使用指南
- [核心模块说明](docs/核心模块说明.md) - 核心模块详细文档
- [LLM集成说明](docs/LLM集成说明.md) - LLM集成指南
- [API参考](docs/API参考.md) - API接口文档

## 示例

查看`examples/`目录获取更多示例：

- `basic_usage.py` - 基础使用示例
- `with_message_platform.py` - 与message_platform集成
- `custom_llm.py` - 自定义LLM客户端

## 许可证

MIT License
