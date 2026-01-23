"""验证新上传文件的实体数量"""
from neo4j import GraphDatabase

uri = "bolt://localhost:7687"
user = "neo4j"
password = "your_password"
driver = GraphDatabase.driver(uri, auth=(user, password))

file_id = "cc2d364a-a69b-4a7b-9384-285074a214bf"

with driver.session() as session:
    # 查询实体数量
    result = session.run("""
        MATCH (m:Message {source_id: $file_id})-[:MENTIONS]->(e:Entity)
        RETURN count(e) as entity_count
    """, file_id=file_id)

    record = result.single()
    if record:
        print(f"✅ 文件 {file_id} 的实体数量: {record['entity_count']}")

    # 显示部分实体
    result = session.run("""
        MATCH (m:Message {source_id: $file_id})-[:MENTIONS]->(e:Entity)
        RETURN e.name as name, e.type as type
        LIMIT 10
    """, file_id=file_id)

    print("\n📝 部分实体:")
    for record in result:
        print(f"  - {record['name']} ({record['type']})")

driver.close()
