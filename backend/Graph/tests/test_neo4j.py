"""
测试 Neo4j 数据库连接和数据
"""
from neo4j import GraphDatabase

# 连接配置
uri = "bolt://localhost:7687"
user = "neo4j"
password = "your_password"

driver = GraphDatabase.driver(uri, auth=(user, password))

def test_connection():
    """测试连接"""
    try:
        driver.verify_connectivity()
        print("✅ Neo4j 连接成功")
        return True
    except Exception as e:
        print(f"❌ Neo4j 连接失败: {e}")
        return False

def count_nodes():
    """统计节点数量"""
    with driver.session() as session:
        # 统计 Message 节点
        result = session.run("MATCH (m:Message) RETURN count(m) as count")
        message_count = result.single()["count"]
        print(f"📊 Message 节点数量: {message_count}")

        # 统计 Entity 节点
        result = session.run("MATCH (e:Entity) RETURN count(e) as count")
        entity_count = result.single()["count"]
        print(f"📊 Entity 节点数量: {entity_count}")

        # 统计关系
        result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
        relation_count = result.single()["count"]
        print(f"📊 关系数量: {relation_count}")

def show_recent_messages():
    """显示最近的 Message 节点"""
    with driver.session() as session:
        result = session.run("""
            MATCH (m:Message)
            RETURN m.id as id, m.source_id as source_id, m.name as name
            ORDER BY m.id DESC
            LIMIT 5
        """)

        print("\n📝 最近的 Message 节点:")
        for record in result:
            print(f"  - id={record['id']}, source_id={record['source_id']}, name={record['name']}")

def show_entities_for_message(source_id):
    """显示指定消息的实体"""
    with driver.session() as session:
        result = session.run("""
            MATCH (m:Message {source_id: $source_id})-[:MENTIONS]->(e:Entity)
            RETURN e.name as name, e.type as type
            LIMIT 10
        """, source_id=source_id)

        print(f"\n🔍 消息 {source_id} 的实体:")
        entities = list(result)
        if entities:
            for record in entities:
                print(f"  - {record['name']} ({record['type']})")
        else:
            print("  ❌ 没有找到实体")

if __name__ == "__main__":
    if test_connection():
        count_nodes()
        show_recent_messages()

        # 如果有消息，显示第一个消息的实体
        with driver.session() as session:
            result = session.run("MATCH (m:Message) RETURN m.source_id as source_id LIMIT 1")
            record = result.single()
            if record:
                show_entities_for_message(record["source_id"])

    driver.close()
