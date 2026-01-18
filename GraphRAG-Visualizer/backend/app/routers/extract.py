"""
实体提取路由
处理文本的实体和关系提取
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import ExtractRequest, ExtractResponse
from app.services.graphrag_service import GraphRAGService

router = APIRouter(prefix="/extract", tags=["extract"])

# 全局 GraphRAG 服务实例
graphrag_service = GraphRAGService()


@router.post("", response_model=ExtractResponse)
async def extract_entities(request: ExtractRequest):
    """
    从文本中提取实体和关系

    Args:
        request: 包含文件 ID、文本内容和语言的请求

    Returns:
        提取的实体和关系列表
    """
    try:
        # 提取实体和关系
        result = await graphrag_service.extract_entities(
            text=request.text,
            language=request.language
        )

        # 构建图谱
        stats = await graphrag_service.build_graph(
            file_id=request.file_id,
            filename=request.file_id,  # 使用 file_id 作为文件名
            page_range=request.page_range or "1-20",
            entities=result['entities'],
            relations=result['relations']
        )

        return ExtractResponse(
            entities=result['entities'],
            relations=result['relations'],
            stats=stats
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"实体提取失败: {str(e)}")
