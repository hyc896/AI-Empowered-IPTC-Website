"""调试删除功能的 404 问题"""
from neo4j import GraphDatabase

# 连接 Neo4j
uri = "bolt://localhost:7687"
auth = ("neo4j", "your_password")
driver = GraphDatabase.driver(uri, auth=auth)

try:
    with driver.session() as session:
        print("=" * 60)
        print("调试删除功能 404 问题")
        print("=" * 60)

        # 1. 查看所有 Message 节点的 id 和 source_id
        print("\n📊 查询所有 Message 节点:")
        result = session.run("""
            MATCH (m:Message)
            RETURN m.id as id, m.source_id as source_id, m.name as name
            ORDER BY m.id DESC
            LIMIT 10
        """)

        for record in result:
            print(f"  id: {record['id']}")
            print(f"  source_id: {record['source_id']}")
            print(f"  name: {record['name']}")
            print("  " + "-" * 50)

        # 2. 测试查询特定的 file_id
        test_file_ids = [
            "33e882ef-2ff5-4af1-8075-139ce7938977",
            "cc2d364a-a69b-4a7b-9384-285074a214bf",
            "2689834e-0c9f-4d0e-8d21-1b06d18ec49d"
        ]

        print("\n🔍 测试查询特定 file_id:")
        for file_id in test_file_ids:
            print(f"\n  查询 file_id: {file_id}")

            # 尝试用 source_id 查询
            result = session.run("""
                MATCH (m:Message)
                WHERE m.source_id = $file_id
                RETURN m.id as message_id, m.source_id as source_id
            """, {"file_id": file_id})

            records = list(result)
            if records:
                print(f"    ✅ 找到 {len(records)} 个匹配的 Message 节点")
                for record in records:
                    print(f"       message_id: {record['message_id']}")
            else:
                print(f"    ❌ 未找到匹配的 Message 节点")

                # 尝试用 id 查询
                result = session.run("""
                    MATCH (m:Message)
                    WHERE m.id = $file_id
                    RETURN m.id as message_id, m.source_id as source_id
                """, {"file_id": file_id})

                records = list(result)
                if records:
                    print(f"    ⚠️  但是用 m.id 可以找到:")
                    for record in records:
                        print(f"       message_id: {record['message_id']}")
                        print(f"       source_id: {record['source_id']}")

finally:
    driver.close()
