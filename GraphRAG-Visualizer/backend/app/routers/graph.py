"""
图谱查询路由
处理图谱数据查询和可视化
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.models.schemas import GraphData
from app.services.graphrag_service import GraphRAGService

router = APIRouter(prefix="/graph", tags=["graph"])

# 全局 GraphRAG 服务实例
graphrag_service = GraphRAGService()


@router.get("/visualize/{file_id}", response_model=GraphData)
async def get_graph_visualization(
    file_id: str,
    page_range: Optional[str] = Query(None, description="页面范围，如 '1-20'")
):
    """
    获取图谱可视化数据

    Args:
        file_id: 文件 ID
        page_range: 页面范围（可选）

    Returns:
        ECharts 格式的图谱数据
    """
    try:
        graph_data = await graphrag_service.get_graph_data(file_id, page_range)
        return GraphData(**graph_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图谱数据失败: {str(e)}")
