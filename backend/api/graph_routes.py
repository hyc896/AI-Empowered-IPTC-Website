# -*- coding: utf-8 -*-
"""
知识图谱API路由
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from backend.services.graph_service import GraphService

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/api/books",
    tags=["知识图谱"]
)

# 创建全局服务实例
graph_service = GraphService()


# 请求/响应模型
class NodeSubgraphRequest(BaseModel):
    """节点子图请求"""
    node_id: str = Field(..., description="节点ID")
    book_id: Optional[str] = Field(None, description="书籍ID")
    depth: int = Field(1, ge=1, le=3, description="扩展深度")


class GraphDataResponse(BaseModel):
    """图谱数据响应"""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class BookListResponse(BaseModel):
    """书籍列表响应"""
    books: List[Dict[str, Any]]


@router.get("/list", response_model=BookListResponse)
async def get_book_list():
    """获取书籍列表

    Returns:
        书籍列表，包含书籍ID、名称、统计信息
    """
    try:
        books = graph_service.get_book_list()
        return BookListResponse(books=books)
    except Exception as e:
        logger.error(f"获取书籍列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取书籍列表失败: {str(e)}")


@router.get("/{book_id}/graph", response_model=GraphDataResponse)
async def get_book_graph(book_id: str):
    """获取指定书籍的知识图谱

    Args:
        book_id: 书籍ID

    Returns:
        图谱数据，包含节点和边
    """
    try:
        graph_data = graph_service.get_book_graph(book_id)
        return GraphDataResponse(**graph_data)
    except Exception as e:
        logger.error(f"获取书籍图谱失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取书籍图谱失败: {str(e)}")


@router.post("/node/subgraph", response_model=GraphDataResponse)
async def get_node_subgraph(request: NodeSubgraphRequest):
    """获取以指定节点为中心的子图

    Args:
        request: 包含节点ID、书籍ID和扩展深度的请求

    Returns:
        子图数据，包含节点和边
    """
    try:
        graph_data = graph_service.get_node_subgraph(
            node_id=request.node_id,
            book_id=request.book_id,
            depth=request.depth
        )
        return GraphDataResponse(**graph_data)
    except ValueError as e:
        logger.error(f"无效的节点ID: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取节点子图失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取节点子图失败: {str(e)}")
