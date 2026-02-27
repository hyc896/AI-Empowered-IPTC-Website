"""
实体提取路由
处理文本的实体和关系提取
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import ExtractRequest, ExtractResponse
from app.services.graphrag_service import graphrag_service

router = APIRouter(prefix="/extract", tags=["extract"])


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
        # 确保服务已初始化
        if graphrag_service.extractor is None:
            from app.config import settings
            await graphrag_service.initialize(settings.GRAPHRAG_CONFIG_PATH)

        # 使用统一的 process_text 方法
        stats = await graphrag_service.process_text(
            text=request.text,
            file_id=request.file_id,
            filename=request.filename,
            page_range=request.page_range or "1-20"
        )

        # 返回统计信息
        return ExtractResponse(
            entities=[],
            relations=[],
            stats=stats
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"实体提取失败: {str(e)}")
