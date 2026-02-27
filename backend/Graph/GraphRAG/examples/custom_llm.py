"""
自定义LLM客户端示例

演示如何实现自定义LLM客户端。
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from graphrag.core.storage import Neo4jStorage
from graphrag.core.entity_extractor import EntityExtractor
from graphrag.core.graph_builder import GraphBuilder
from graphrag.llm.base import BaseLLMClient
from graphrag.utils.config_loader import ConfigLoader


class MyCustomLLM(BaseLLMClient):
    """自定义LLM客户端示例"""

    def __init__(self, api_key: str, model: str = "my-model"):
        """初始化自定义LLM客户端

        Args:
            api_key: API密钥
            model: 模型名称
        """
        self.api_key = api_key
        self.model = model
        print(f"初始化自定义LLM客户端: {model}")

    async def generate_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """异步生成文本

        这里应该实现你的LLM API调用逻辑。
        为了演示，我们返回一个模拟的响应。

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数

        Returns:
            str: 生成的文本
        """
        # 模拟API调用
        await asyncio.sleep(0.1)

        # 返回模拟的实体提取结果
        mock_response = """
        {
          "entities": [
            {
              "name": "示例公司",
              "type": "Company",
              "aliases": [],
              "attributes": {"country": "中国"}
            },
            {
              "name": "张三",
              "type": "Person",
              "aliases": [],
              "attributes": {}
            }
          ],
          "relations": [
            {
              "source": "张三",
              "target": "示例公司",
              "type": "WORKS_AT",
              "properties": {"role": "CEO"}
            }
          ]
        }
        """

        return mock_response

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """同步生成文本

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数

        Returns:
            str: 生成的文本
        """
        # 同步版本：使用asyncio.run调用异步方法
        return asyncio.run(self.generate_async(messages, temperature, max_tokens, **kwargs))


async def main():
    # 加载配置
    config_path = Path(__file__).parent.parent / "config" / "default_config.yaml"
    config = ConfigLoader.load_config(str(config_path))

    # 初始化Neo4j存储
    storage = Neo4jStorage()
    storage.initialize(config['neo4j'])
    print("Neo4j连接成功")

    # 使用自定义LLM客户端
    my_llm = MyCustomLLM(api_key="your_api_key", model="my-custom-model")

    # 初始化实体提取器
    extractor = EntityExtractor(my_llm)

    # 初始化图谱构建器
    builder = GraphBuilder(storage)

    # 待处理的文本
    text = """
    示例公司是一家科技公司，由张三创立。
    张三担任示例公司的CEO。
    """

    print("\n开始提取实体和关系（使用自定义LLM）...")
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
        "title": "示例新闻",
        "content": text,
        "url": "https://example.com/news/custom",
        "published_at": "2025-01-01T00:00:00",
        "crawled_at": "2025-01-01T00:00:00"
    }

    stats = await builder.add_document_with_entities(
        doc_id="doc_custom_001",
        doc_data=doc_data,
        entities=result['entities'],
        relations=result['relations']
    )

    print(f"图谱构建完成:")
    print(f"  - 创建实体: {stats.get('entities_created', 0)}")
    print(f"  - 创建关系: {stats.get('relations_created', 0)}")

    # 关闭连接
    storage.close()
    print("\n完成！")


if __name__ == "__main__":
    asyncio.run(main())
