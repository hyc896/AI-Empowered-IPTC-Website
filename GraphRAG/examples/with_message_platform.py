"""
与message_platform集成示例

演示如何复用message_platform的配置和LLM客户端。
"""

import asyncio
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "message_platform"))

from graphrag.core.storage import Neo4jStorage
from graphrag.core.entity_extractor import EntityExtractor
from graphrag.core.graph_builder import GraphBuilder

# 导入message_platform的模块
try:
    from message_platform.llm import global_llm_manager
    from message_platform.config import config_manager
    from message_platform.database import create_session
    from message_platform.database.entities import TongHuaShunMessage
except ImportError:
    print("错误: 无法导入message_platform模块")
    print("请确保message_platform在正确的路径")
    sys.exit(1)


async def main():
    # 使用message_platform的配置
    mp_config = config_manager.get_config()

    # 初始化Neo4j存储（复用message_platform的配置）
    storage = Neo4jStorage()
    neo4j_config = mp_config.get("database", {}).get("neo4j", {})
    storage.initialize(neo4j_config)
    print("Neo4j连接成功（复用message_platform配置）")

    # 使用message_platform的LLM客户端
    llm_client = global_llm_manager.fast_client or global_llm_manager.chat_client
    if not llm_client:
        print("错误: message_platform的LLM客户端未初始化")
        sys.exit(1)
    print("使用message_platform的LLM客户端")

    # 初始化实体提取器
    extractor = EntityExtractor(llm_client)

    # 初始化图谱构建器
    builder = GraphBuilder(storage)

    # 从message_platform数据库读取消息
    print("\n从message_platform数据库读取消息...")
    with create_session() as db:
        messages = db.query(TongHuaShunMessage).limit(5).all()
        print(f"读取到 {len(messages)} 条消息")

        for msg in messages:
            print(f"\n处理消息: {msg.title}")

            # 提取实体
            text = f"{msg.title}\n\n{msg.content}"
            result = await extractor.extract_entities(text)

            print(f"  提取到 {len(result['entities'])} 个实体")
            print(f"  提取到 {len(result['relations'])} 个关系")

            # 构建图谱
            doc_data = {
                "source_id": msg.source_id,
                "title": msg.title,
                "content": msg.content,
                "url": msg.url,
                "published_at": msg.published_at.isoformat() if msg.published_at else "",
                "crawled_at": msg.crawled_at.isoformat() if msg.crawled_at else ""
            }

            stats = await builder.add_document_with_entities(
                doc_id=str(msg.id),
                doc_data=doc_data,
                entities=result['entities'],
                relations=result['relations']
            )

            print(f"  图谱构建完成: 实体 {stats.get('entities_created', 0)}, "
                  f"关系 {stats.get('relations_created', 0)}")

    # 关闭连接
    storage.close()
    print("\n完成！")


if __name__ == "__main__":
    asyncio.run(main())
