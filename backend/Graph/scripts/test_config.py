# -*- coding: utf-8 -*-
"""
测试GraphRAG配置和Neo4j连接
"""
import sys
from pathlib import Path

# 添加GraphRAG到Python路径
graphrag_path = Path(__file__).parent.parent / "GraphRAG"
sys.path.insert(0, str(graphrag_path))

print("="*80)
print("GraphRAG配置和连接测试")
print("="*80)

# 测试1: 导入GraphRAG模块
print("\n[测试1] 导入GraphRAG模块...")
try:
    from graphrag.utils.config_loader import ConfigLoader
    from graphrag.core.storage import Neo4jStorage
    print("[OK] GraphRAG模块导入成功")
except Exception as e:
    print(f"[FAIL] GraphRAG模块导入失败: {e}")
    sys.exit(1)

# 测试2: 加载配置文件
print("\n[测试2] 加载配置文件...")
config_path = Path(__file__).parent.parent / "GraphRAG" / "config" / "default_config.yaml"
print(f"配置文件路径: {config_path}")

try:
    config = ConfigLoader.load_config(str(config_path))
    print("[OK] 配置文件加载成功")

    # 显示关键配置
    print("\n关键配置信息:")
    print(f"  LLM模型: {config['llm']['model']}")
    print(f"  LLM提供商: {config['llm']['provider']}")
    print(f"  Neo4j URI: {config['neo4j']['uri']}")
    print(f"  Neo4j数据库: {config['neo4j']['database']}")

except Exception as e:
    print(f"[FAIL] 配置文件加载失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试3: 验证配置
print("\n[测试3] 验证配置...")
try:
    if ConfigLoader.validate_config(config):
        print("[OK] 配置验证通过")
    else:
        print("[FAIL] 配置验证失败")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] 配置验证失败: {e}")
    sys.exit(1)

# 测试4: 测试Neo4j连接
print("\n[测试4] 测试Neo4j连接...")
try:
    storage = Neo4jStorage()
    storage.initialize(config['neo4j'])
    print("[OK] Neo4j连接成功")

    # 测试简单查询
    result = storage.execute_read("RETURN 1 as test")
    if result:
        print("[OK] Neo4j查询测试成功")

    storage.close()
    print("[OK] Neo4j连接已关闭")

except Exception as e:
    print(f"[FAIL] Neo4j连接失败: {e}")
    import traceback
    traceback.print_exc()
    print("\n提示: 请检查Neo4j连接信息是否正确")
    sys.exit(1)

print("\n" + "="*80)
print("所有测试通过！GraphRAG配置正常")
print("="*80)
