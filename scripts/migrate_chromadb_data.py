#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ChromaDB历史数据迁移脚本
- 合并 tonghuashun_messages + tonghuashun → tonghuashun
- 重命名 personal_agent_kr36 → kr36
- 重命名 personal_agent_arxiv_messages → arxiv
- 不迁移 personal_agent_memory
"""

import os
import sys
import logging
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_chromadb():
    """初始化ChromaDB连接"""
    try:
        import chromadb
        # 连接到现有的ChromaDB数据库
        client = chromadb.PersistentClient(path="./data/chromadb")
        logger.info("ChromaDB连接成功")
        return client
    except Exception as e:
        logger.error(f"ChromaDB连接失败: {e}")
        raise

def get_collection_info(client, collection_name: str) -> Dict[str, Any]:
    """获取collection信息"""
    try:
        collection = client.get_collection(collection_name)
        count = collection.count()
        return {
            "exists": True,
            "count": count,
            "collection": collection
        }
    except Exception as e:
        logger.warning(f"Collection {collection_name} 不存在: {e}")
        return {
            "exists": False,
            "count": 0,
            "collection": None
        }

def merge_tonghuashun_collections(client):
    """合并tonghuashun相关collections"""
    logger.info("=== 开始合并tonghuashun数据 ===")

    # 获取源collections信息
    messages_info = get_collection_info(client, "personal_agent_tonghuashun_messages")
    tonghuashun_info = get_collection_info(client, "personal_agent_tonghuashun")

    total_messages = messages_info["count"] + tonghuashun_info["count"]
    logger.info(f"待合并数据: tonghuashun_messages({messages_info['count']}条) + tonghuashun({tonghuashun_info['count']}条) = {total_messages}条")

    if total_messages == 0:
        logger.warning("没有数据需要合并")
        return

    try:
        # 创建目标collection
        target_collection = client.get_or_create_collection("tonghuashun")
        logger.info("创建目标collection: tonghuashun")

        batch_size = 500  # 批量处理大小

        # 合并 personal_agent_tonghuashun_messages
        if messages_info["exists"] and messages_info["count"] > 0:
            logger.info("开始迁移 personal_agent_tonghuashun_messages...")
            source_collection = messages_info["collection"]

            for offset in range(0, messages_info["count"], batch_size):
                batch = source_collection.get(
                    include=["metadatas", "documents", "embeddings"],
                    limit=batch_size,
                    offset=offset
                )

                target_collection.upsert(
                    ids=batch["ids"],
                    documents=batch["documents"],
                    metadatas=batch["metadatas"],
                    embeddings=batch["embeddings"]
                )

                logger.info(f"已迁移 {min(offset + batch_size, messages_info['count'])}/{messages_info['count']} 条消息")

        # 合并 personal_agent_tonghuashun
        if tonghuashun_info["exists"] and tonghuashun_info["count"] > 0:
            logger.info("开始迁移 personal_agent_tonghuashun...")
            source_collection = tonghuashun_info["collection"]

            for offset in range(0, tonghuashun_info["count"], batch_size):
                batch = source_collection.get(
                    include=["metadatas", "documents", "embeddings"],
                    limit=batch_size,
                    offset=offset
                )

                target_collection.upsert(
                    ids=batch["ids"],
                    documents=batch["documents"],
                    metadatas=batch["metadatas"],
                    embeddings=batch["embeddings"]
                )

                logger.info(f"已迁移 {min(offset + batch_size, tonghuashun_info['count'])}/{tonghuashun_info['count']} 条消息")

        # 验证合并结果
        final_count = target_collection.count()
        logger.info(f"✅ tonghuashun合并完成: {final_count}条数据")

        # 备份原collections
        logger.info("备份原collections...")
        try:
            if messages_info["exists"]:
                messages_info["collection"].modify(name="personal_agent_tonghuashun_messages_backup")
                logger.info("✅ personal_agent_tonghuashun_messages → personal_agent_tonghuashun_messages_backup")

            if tonghuashun_info["exists"]:
                tonghuashun_info["collection"].modify(name="personal_agent_tonghuashun_backup")
                logger.info("✅ personal_agent_tonghuashun → personal_agent_tonghuashun_backup")

        except Exception as e:
            logger.warning(f"备份collection失败: {e}")

    except Exception as e:
        logger.error(f"合并tonghuashun数据失败: {e}")
        raise

def rename_collections(client):
    """重命名其他collections"""
    logger.info("=== 开始重命名collections ===")

    rename_mapping = {
        "personal_agent_kr36": "kr36",
        "personal_agent_arxiv_messages": "arxiv"
        # 注意：不迁移 personal_agent_memory
    }

    for old_name, new_name in rename_mapping.items():
        try:
            info = get_collection_info(client, old_name)
            if not info["exists"]:
                logger.warning(f"Collection {old_name} 不存在，跳过")
                continue

            logger.info(f"重命名 {old_name} → {new_name} ({info['count']}条数据)")
            info["collection"].modify(name=new_name)
            logger.info(f"✅ {old_name} → {new_name}")

        except Exception as e:
            logger.error(f"重命名 {old_name} 失败: {e}")
            continue

def validate_migration(client):
    """验证迁移结果"""
    logger.info("=== 验证迁移结果 ===")

    expected_collections = ["tonghuashun", "kr36", "arxiv", "personal_agent_memory"]

    for collection_name in expected_collections:
        info = get_collection_info(client, collection_name)
        if info["exists"]:
            logger.info(f"✅ {collection_name}: {info['count']}条数据")
        else:
            logger.warning(f"❌ {collection_name}: 不存在")

    # 检查备份collections
    backup_collections = ["personal_agent_tonghuashun_messages_backup", "personal_agent_tonghuashun_backup"]
    logger.info("备份collections:")
    for collection_name in backup_collections:
        info = get_collection_info(client, collection_name)
        if info["exists"]:
            logger.info(f"✅ {collection_name}: {info['count']}条数据")

def main():
    """主函数"""
    logger.info("开始ChromaDB数据迁移...")

    try:
        # 确保在正确的目录
        if not os.path.exists("./data/chromadb"):
            logger.error("未找到 ./data/chromadb 目录，请在项目根目录运行此脚本")
            return False

        # 连接ChromaDB
        client = setup_chromadb()

        # 显示迁移前的状态
        logger.info("=== 迁移前状态 ===")
        all_collections = client.list_collections()
        for collection in all_collections:
            count = collection.count()
            logger.info(f"  {collection.name}: {count}条数据")

        # 执行迁移
        merge_tonghuashun_collections(client)
        rename_collections(client)

        # 验证结果
        validate_migration(client)

        logger.info("🎉 ChromaDB数据迁移完成！")
        return True

    except Exception as e:
        logger.error(f"迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)