#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""批量向量化已存在的消息"""

import sys
import asyncio
from pathlib import Path
from typing import List, Dict, Any
import logging

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.database.connection import create_session
from backend.storage.chromadb_storage import ChromaDBStorage
from backend.config.config_manager import ConfigManager
from backend.llm import get_embedding_client
from backend.llm.global_llm_manager import initialize_llm
from sqlalchemy import text
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageVectorizer:
    """消息向量化器"""

    def __init__(self):
        """初始化向量化器"""
        # 加载配置
        config_manager = ConfigManager()
        config_manager.load_config('config.yaml')
        self.config = config_manager.get_config()

        # 初始化ChromaDB
        chroma_config = self.config.get('database', {}).get('chromadb', {})
        self.chroma_storage = ChromaDBStorage()
        self.chroma_storage.initialize(chroma_config)

        # 初始化GlobalLLMManager
        llm_config = self.config.get('llm', {})
        chat_config = llm_config.get('chat', {})
        embedding_config = llm_config.get('embedding', {})
        fast_config = llm_config.get('fast', {})
        initialize_llm(chat_config, embedding_config, fast_config)

        # 获取Embedding客户端
        self.embedding_client = get_embedding_client()

        if self.embedding_client is None:
            raise RuntimeError("Embedding客户端初始化失败")

        logger.info("向量化器初始化完成")

    def get_message_sources(self) -> List[Dict[str, Any]]:
        """获取所有消息源配置"""
        with create_session() as session:
            result = session.execute(text("""
                SELECT id, name, config
                FROM mp_message_sources
                WHERE is_active = 1
            """))

            sources = []
            for row in result:
                import json
                config = json.loads(row[2]) if isinstance(row[2], str) else row[2]
                sources.append({
                    'id': row[0],
                    'name': row[1],
                    'mysql_table': config.get('mysql_table'),
                    'chroma_collection': config.get('chroma_collection')
                })

            return sources

    def vectorize_source(self, source: Dict[str, Any], batch_size: int = 50) -> Dict[str, Any]:
        """
        向量化单个消息源的所有消息

        Args:
            source: 消息源配置
            batch_size: 批量处理大小

        Returns:
            处理结果统计
        """
        table_name = source['mysql_table']
        collection_name = source['chroma_collection']
        source_name = source['name']

        logger.info(f"开始向量化消息源: {source_name}")
        logger.info(f"  MySQL表: {table_name}")
        logger.info(f"  ChromaDB集合: {collection_name}")

        # 创建或获取collection
        self.chroma_storage.create_collection(collection_name)

        # 统计信息
        stats = {
            'source_name': source_name,
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }

        try:
            with create_session() as session:
                # 获取消息总数
                count_result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                total_count = count_result.scalar()
                stats['total'] = total_count

                if total_count == 0:
                    logger.info(f"  消息源 {source_name} 没有消息，跳过")
                    return stats

                logger.info(f"  找到 {total_count} 条消息")

                # 分批处理
                offset = 0
                while offset < total_count:
                    # 获取一批消息
                    query = text(f"""
                        SELECT id, title, content, summary, url, published_at
                        FROM {table_name}
                        ORDER BY id
                        LIMIT :limit OFFSET :offset
                    """)
                    result = session.execute(query, {'limit': batch_size, 'offset': offset})
                    messages = result.fetchall()

                    if not messages:
                        break

                    # 向量化这批消息
                    batch_stats = self._vectorize_batch(messages, collection_name)
                    stats['success'] += batch_stats['success']
                    stats['failed'] += batch_stats['failed']
                    stats['skipped'] += batch_stats['skipped']

                    offset += batch_size
                    logger.info(f"  进度: {min(offset, total_count)}/{total_count} ({min(offset, total_count)*100//total_count}%)")

                logger.info(f"完成向量化: {source_name}")
                logger.info(f"  成功: {stats['success']}, 失败: {stats['failed']}, 跳过: {stats['skipped']}")

        except Exception as e:
            logger.error(f"向量化消息源失败: {source_name}, 错误: {e}")
            stats['failed'] = stats['total']

        return stats

    def _vectorize_batch(self, messages: List[Any], collection_name: str) -> Dict[str, int]:
        """
        向量化一批消息

        Args:
            messages: 消息列表
            collection_name: ChromaDB集合名称

        Returns:
            批次处理统计
        """
        stats = {'success': 0, 'failed': 0, 'skipped': 0}

        for message in messages:
            try:
                msg_id = message[0]
                title = message[1] or ''
                content = message[2] or ''
                summary = message[3] or ''
                url = message[4] or ''

                # 构建文档文本（用于向量化）
                document_text = f"{title}\n{summary or content[:500]}"

                if not document_text.strip():
                    stats['skipped'] += 1
                    continue

                # 生成embedding
                embedding = self.embedding_client.generate_embedding(document_text)

                # 使用消息ID作为ChromaDB的ID
                chroma_id = str(msg_id)

                # 存储到ChromaDB
                self.chroma_storage.upsert(
                    collection_name=collection_name,
                    ids=[chroma_id],
                    documents=[document_text],
                    metadatas=[{
                        'id': str(msg_id),
                        'title': title[:500] if title else '',
                        'url': url[:500] if url else '',
                        'published_at': str(message[5]) if message[5] else ''
                    }],
                    embeddings=[embedding]
                )

                stats['success'] += 1

            except Exception as e:
                logger.error(f"向量化消息失败: {message[0]}, 错误: {e}")
                stats['failed'] += 1

        return stats


def main():
    """主函数：批量向量化所有消息"""
    logger.info("=" * 60)
    logger.info("开始批量向量化消息")
    logger.info("=" * 60)

    # 初始化向量化器
    vectorizer = MessageVectorizer()

    # 获取所有消息源
    sources = vectorizer.get_message_sources()
    logger.info(f"找到 {len(sources)} 个活跃的消息源")

    # 总体统计
    total_stats = {
        'total_sources': len(sources),
        'total_messages': 0,
        'total_success': 0,
        'total_failed': 0,
        'total_skipped': 0
    }

    # 逐个处理消息源
    for i, source in enumerate(sources, 1):
        logger.info(f"\n[{i}/{len(sources)}] 处理消息源: {source['name']}")

        stats = vectorizer.vectorize_source(source)

        total_stats['total_messages'] += stats['total']
        total_stats['total_success'] += stats['success']
        total_stats['total_failed'] += stats['failed']
        total_stats['total_skipped'] += stats['skipped']

    # 输出总体统计
    logger.info("\n" + "=" * 60)
    logger.info("向量化完成！")
    logger.info("=" * 60)
    logger.info(f"处理消息源数量: {total_stats['total_sources']}")
    logger.info(f"消息总数: {total_stats['total_messages']}")
    logger.info(f"成功: {total_stats['total_success']}")
    logger.info(f"失败: {total_stats['total_failed']}")
    logger.info(f"跳过: {total_stats['total_skipped']}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

