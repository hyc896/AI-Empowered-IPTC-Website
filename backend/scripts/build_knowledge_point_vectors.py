# -*- coding: utf-8 -*-
"""
构建知识点向量库
"""
import json
import sys
import os
import asyncio
from pathlib import Path

# 设置控制台输出编码为UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加backend目录到path
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

from llm.global_llm_manager import GlobalLLMManager
from config import GlobalConfig
import chromadb


def initialize_managers():
    """初始化LLM管理器和ChromaDB"""
    # 加载配置
    config_instance = GlobalConfig.get_instance()
    config_path = project_root / "config.yaml"
    config_instance.initialize(str(config_path))

    # 获取LLM配置
    llm_config = config_instance.get_config('llm', {})
    chat_config = llm_config.get('chat', {})
    embedding_config = llm_config.get('embedding', {})
    fast_config = llm_config.get('fast', {})

    # 初始化LLM管理器
    llm_manager = GlobalLLMManager.get_instance()
    llm_manager.initialize(chat_config, embedding_config, fast_config)

    print("[初始化] LLM管理器初始化成功")
    print(f"  Embedding模型: {embedding_config.get('model')}")

    # 初始化ChromaDB（直接使用chromadb）
    chroma_config = config_instance.get_config('database.chromadb', {})
    if chroma_config:
        # 使用本地持久化客户端
        chroma_path = chroma_config.get('path', './data/chromadb')
        # 如果是相对路径，转换为相对于项目根目录的路径
        if not os.path.isabs(chroma_path):
            chroma_path = os.path.join(project_root, chroma_path)
        print(f"  ChromaDB路径: {chroma_path}")
        chroma_client = chromadb.PersistentClient(path=chroma_path)

        # 创建或获取知识点collection
        collection = chroma_client.get_or_create_collection(
            name="iptc_knowledge_points",
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )

        print(f"[初始化] ChromaDB初始化成功")
        print(f"  数据路径: {chroma_path}")
        print(f"  Collection: iptc_knowledge_points")
    else:
        print("[错误] ChromaDB配置未找到")
        sys.exit(1)

    return llm_manager, collection


async def build_knowledge_point_vectors():
    """
    将知识点向量化并存入ChromaDB
    """
    # 初始化管理器
    llm_manager, collection = initialize_managers()

    # 读取知识点
    data_dir = Path(__file__).parent.parent / "data"
    knowledge_points_file = data_dir / "knowledge_points.json"

    print(f"\n正在读取知识点: {knowledge_points_file}")

    with open(knowledge_points_file, 'r', encoding='utf-8') as f:
        knowledge_points = json.load(f)

    print(f"开始向量化 {len(knowledge_points)} 个知识点...")
    print(f"目标Collection: iptc_knowledge_points\n")

    success_count = 0
    failed_count = 0

    for i, kp in enumerate(knowledge_points, 1):
        try:
            # 生成唯一ID（使用章节ID + 索引）
            kp_id = f"{kp['chapter_id']}_{i:02d}"

            # 使用embedding_text进行向量化
            embedding_text = kp['embedding_text']

            print(f"[{i}/{len(knowledge_points)}] 向量化: {kp['name']}")
            print(f"  文本长度: {len(embedding_text)} 字符")

            # 调用Embedding模型（使用同步方法）
            embedding = llm_manager.embedding_client.generate_embedding(embedding_text)

            # 验证embedding向量
            if not embedding or len(embedding) == 0:
                print(f"  [警告] 未能获取embedding向量，跳过")
                failed_count += 1
                continue

            # 准备元数据
            metadata = {
                "name": kp['name'],
                "chapter": kp['chapter'],
                "chapter_id": kp['chapter_id'],
                "application_scenarios": json.dumps(kp['application_scenarios'], ensure_ascii=False),
                "typical_keywords": json.dumps(kp['typical_keywords'], ensure_ascii=False)
            }

            # 存入ChromaDB
            collection.add(
                ids=[kp_id],
                embeddings=[embedding],
                documents=[kp['theory_description']],
                metadatas=[metadata]
            )

            print(f"  [成功] 已存入ChromaDB (ID: {kp_id})")
            success_count += 1

        except Exception as e:
            print(f"  [错误] 向量化失败: {e}")
            import traceback
            traceback.print_exc()
            failed_count += 1

    print(f"\n{'='*60}")
    print(f"[完成] 知识点向量库构建完成！")
    print(f"  成功: {success_count} 个")
    print(f"  失败: {failed_count} 个")
    print(f"  Collection: iptc_knowledge_points")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(build_knowledge_point_vectors())
