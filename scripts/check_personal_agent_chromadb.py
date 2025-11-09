# -*- coding: utf-8 -*-

"""
检查personal_agent的ChromaDB数据
查看可以迁移的collection
"""

import chromadb

def check_personal_agent_chromadb():
    """检查personal_agent的ChromaDB"""

    print("\n" + "=" * 80)
    print("PERSONAL_AGENT - ChromaDB数据检查")
    print("=" * 80)

    personal_agent_path = "d:/TechWork/personal_agent/data/chromadb"
    print(f"\nChromaDB路径: {personal_agent_path}")

    try:
        client = chromadb.PersistentClient(path=personal_agent_path)
        collections = client.list_collections()

        print(f"\n找到 {len(collections)} 个collection:")
        print("-" * 80)

        if not collections:
            print("\n[提示] 未找到任何collection")
        else:
            total_records = 0
            for collection in collections:
                try:
                    count = collection.count()
                    total_records += count
                    print(f"\nCollection: {collection.name}")
                    print(f"  记录数: {count} 条")

                    # 显示部分metadata信息
                    if count > 0:
                        sample = collection.get(limit=1)
                        if sample and 'metadatas' in sample and sample['metadatas']:
                            metadata = sample['metadatas'][0]
                            source_id = metadata.get('source_id', 'N/A')
                            print(f"  Source ID: {source_id}")

                except Exception as e:
                    print(f"\nCollection: {collection.name}")
                    print(f"  记录数: [查询失败] - {e}")

            print("\n" + "-" * 80)
            print(f"\n总计: {total_records} 条向量记录")

        print("\n【可迁移mapping】")
        print("-" * 80)
        print("personal_agent_tonghuashun → message_platform: tonghuashun")
        print("personal_agent_kr36 → message_platform: kr36")
        print("personal_agent_arxiv → message_platform: arxiv")

    except Exception as e:
        print(f"\n[错误] ChromaDB连接失败: {e}")
        print(f"请确认路径是否正确: {personal_agent_path}")

    print("\n" + "=" * 80)
    print("检查完成")
    print("=" * 80 + "\n")

if __name__ == '__main__':
    check_personal_agent_chromadb()
