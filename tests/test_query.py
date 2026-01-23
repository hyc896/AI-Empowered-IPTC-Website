"""
测试后端查询语句
"""
from neo4j import GraphDatabase

uri = "bolt://localhost:7687"
user = "neo4j"
password = "your_password"

driver = GraphDatabase.driver(uri, auth=(user, password))

def test_current_query():
    """测试当前的查询语句"""
    query = """
    MATCH (m:Message)
    OPTIONAL MATCH (m)-[:MENTIONS]->(e:Entity)
    WITH m.source_id as file_id, m.name as name, count(DISTINCT e) as entity_count
    RETURN file_id, name, entity_count
    ORDER BY file_id DESC
    """

    with driver.session() as session:
        results = session.run(query)

        print("📊 查询结果:")
        for record in results:
            file_id = record.get('file_id')
            name = record.get('name')
            entity_count = record.get('entity_count')
            print(f"  file_id={file_id}, name={name}, entity_count={entity_count}")

def test_specific_file():
    """测试特定文件的实体数量"""
    query = """
    MATCH (m:Message {source_id: $source_id})-[:MENTIONS]->(e:Entity)
    RETURN count(e) as entity_count
    """

    # 使用测试脚本中看到的 source_id
    source_id = "db08c0ce-ca5f-41ac-9820-2d47264fce77"

    with driver.session() as session:
        result = session.run(query, source_id=source_id)
        record = result.single()
        if record:
            print(f"\n🔍 文件 {source_id} 的实体数量: {record['entity_count']}")

if __name__ == "__main__":
    test_current_query()
    test_specific_file()
    driver.close()
