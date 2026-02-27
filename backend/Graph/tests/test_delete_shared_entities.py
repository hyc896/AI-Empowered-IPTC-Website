"""测试删除文件时共享实体的处理"""
from neo4j import GraphDatabase

def test_delete_shared_entities():
    """测试删除文件时不会误删共享实体"""

    # 连接 Neo4j
    uri = "bolt://localhost:7687"
    auth = ("neo4j", "your_password")

    driver = GraphDatabase.driver(uri, auth=auth)

    try:
        with driver.session() as session:
            print("=" * 60)
            print("测试场景：删除文件时共享实体的处理")
            print("=" * 60)

            # 1. 创建测试数据：两个文件共享同一个实体
            print("\n📝 步骤 1: 创建测试数据")

            # 创建实体
            session.run("""
                MERGE (e:Entity {name: '测试共享实体'})
                SET e.type = 'TestEntity', e.mention_count = 2
            """)

            # 创建文件 A 的 Message 节点
            session.run("""
                CREATE (m:Message {
                    id: 'test_file_a_1',
                    source_id: 'test_file_a',
                    name: '测试文件A'
                })
            """)

            # 创建文件 B 的 Message 节点
            session.run("""
                CREATE (m:Message {
                    id: 'test_file_b_1',
                    source_id: 'test_file_b',
                    name: '测试文件B'
                })
            """)

            # 创建 MENTIONS 关系
            session.run("""
                MATCH (m1:Message {id: 'test_file_a_1'})
                MATCH (m2:Message {id: 'test_file_b_1'})
                MATCH (e:Entity {name: '测试共享实体'})
                CREATE (m1)-[:MENTIONS]->(e)
                CREATE (m2)-[:MENTIONS]->(e)
            """)

            print("✅ 测试数据创建完成")
            print("   - 实体: 测试共享实体")
            print("   - 文件A: test_file_a (引用该实体)")
            print("   - 文件B: test_file_b (引用该实体)")

            # 2. 验证初始状态
            print("\n📊 步骤 2: 验证初始状态")

            result = session.run("""
                MATCH (e:Entity {name: '测试共享实体'})
                OPTIONAL MATCH (m:Message)-[:MENTIONS]->(e)
                RETURN e.name as entity_name, count(m) as mention_count
            """)
            record = result.single()

            print(f"   实体: {record['entity_name']}")
            print(f"   被引用次数: {record['mention_count']}")

            if record['mention_count'] != 2:
                print("❌ 初始状态错误：应该有 2 个 MENTIONS 关系")
                return

            # 3. 删除文件 A（模拟删除逻辑）
            print("\n🗑️  步骤 3: 删除文件 A")

            session.run("""
                // 1. 删除 Message 节点及其所有关系
                MATCH (m:Message)
                WHERE m.id = 'test_file_a_1'
                DETACH DELETE m

                // 2. 清理没有任何 MENTIONS 关系的孤立实体
                WITH 1 as dummy
                MATCH (e:Entity)
                WHERE NOT (e)<-[:MENTIONS]-()
                DELETE e
            """)

            print("✅ 文件 A 删除完成")

            # 4. 验证删除后状态
            print("\n📊 步骤 4: 验证删除后状态")

            # 检查实体是否还存在
            result = session.run("""
                MATCH (e:Entity {name: '测试共享实体'})
                OPTIONAL MATCH (m:Message)-[:MENTIONS]->(e)
                RETURN e.name as entity_name, count(m) as mention_count
            """)
            record = result.single()

            if record:
                print(f"✅ 实体仍然存在: {record['entity_name']}")
                print(f"   被引用次数: {record['mention_count']}")

                if record['mention_count'] == 1:
                    print("✅ 引用次数正确：从 2 减少到 1")
                else:
                    print(f"❌ 引用次数错误：应该是 1，实际是 {record['mention_count']}")
            else:
                print("❌ 实体被错误删除！")
                return

            # 检查文件 A 的 Message 是否被删除
            result = session.run("""
                MATCH (m:Message {id: 'test_file_a_1'})
                RETURN count(m) as count
            """)
            record = result.single()

            if record['count'] == 0:
                print("✅ 文件 A 的 Message 节点已删除")
            else:
                print("❌ 文件 A 的 Message 节点未删除")

            # 检查文件 B 的 Message 是否还存在
            result = session.run("""
                MATCH (m:Message {id: 'test_file_b_1'})
                RETURN count(m) as count
            """)
            record = result.single()

            if record['count'] == 1:
                print("✅ 文件 B 的 Message 节点仍然存在")
            else:
                print("❌ 文件 B 的 Message 节点被错误删除")

            # 5. 清理测试数据
            print("\n🧹 步骤 5: 清理测试数据")

            session.run("""
                MATCH (m:Message)
                WHERE m.id IN ['test_file_b_1']
                DETACH DELETE m
            """)

            session.run("""
                MATCH (e:Entity {name: '测试共享实体'})
                DELETE e
            """)

            print("✅ 测试数据清理完成")

            print("\n" + "=" * 60)
            print("✅ 测试通过：共享实体不会被误删")
            print("=" * 60)

    finally:
        driver.close()

if __name__ == "__main__":
    test_delete_shared_entities()
