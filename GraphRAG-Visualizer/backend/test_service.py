"""
后端服务测试脚本
测试 PDF 处理和基本功能
"""
import sys
from pathlib import Path

# 添加 app 到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.pdf_service import PDFService
from app.config import settings

def test_pdf_service():
    """测试 PDF 服务"""
    print("=" * 50)
    print("测试 PDF 服务")
    print("=" * 50)

    # 测试配置
    print(f"\n✓ 配置加载成功")
    print(f"  - 上传目录: {settings.UPLOAD_DIR}")
    print(f"  - 默认页面范围: {settings.DEFAULT_PAGE_RANGE}")
    print(f"  - GraphRAG 配置: {settings.GRAPHRAG_CONFIG_PATH}")

    # 测试页面范围验证
    print(f"\n✓ 测试页面范围验证")
    start, end = PDFService.validate_page_range(100, 1, 20)
    print(f"  - 输入: (1, 20), 总页数: 100")
    print(f"  - 输出: ({start}, {end})")

    start, end = PDFService.validate_page_range(10, 1, 20)
    print(f"  - 输入: (1, 20), 总页数: 10")
    print(f"  - 输出: ({start}, {end})")

    print("\n✅ PDF 服务测试通过")

def test_imports():
    """测试模块导入"""
    print("\n" + "=" * 50)
    print("测试模块导入")
    print("=" * 50)

    try:
        from app.models.schemas import UploadResponse, ExtractRequest, GraphData
        print("\n✓ 数据模型导入成功")

        from app.routers import upload, extract, graph
        print("✓ 路由模块导入成功")

        from app.services.graphrag_service import GraphRAGService
        print("✓ GraphRAG 服务导入成功")

        print("\n✅ 所有模块导入测试通过")
        return True
    except Exception as e:
        print(f"\n❌ 模块导入失败: {e}")
        return False

if __name__ == "__main__":
    print("\n🚀 开始测试后端服务\n")

    # 测试导入
    if not test_imports():
        sys.exit(1)

    # 测试 PDF 服务
    test_pdf_service()

    print("\n" + "=" * 50)
    print("✅ 所有测试通过！")
    print("=" * 50)
    print("\n💡 下一步:")
    print("  1. 确保 Neo4j 数据库运行")
    print("  2. 配置 GraphRAG (config/default_config.yaml)")
    print("  3. 启动服务: python -m uvicorn app.main:app --reload")
    print("  4. 访问文档: http://localhost:8000/docs\n")
