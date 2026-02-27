"""
书籍知识图谱路由
处理书籍上传、图谱查询和节点扩展
"""
from fastapi import APIRouter, HTTPException
from typing import Optional

from app.services.graphrag_service import graphrag_service
from app.models.schemas import BookListResponse, BookInfo, GraphData, NodeSubgraphRequest

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/list", response_model=BookListResponse)
async def get_books():
    """
    获取所有已上传的书籍列表

    Returns:
        书籍列表
    """
    try:
        books = await graphrag_service.get_all_books()
        return BookListResponse(
            books=[BookInfo(**book) for book in books],
            total=len(books)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取书籍列表失败: {str(e)}")


@router.get("/{book_id}/graph", response_model=GraphData)
async def get_book_graph(book_id: str):
    """
    获取指定书籍的知识图谱

    Args:
        book_id: 书籍ID

    Returns:
        图谱数据
    """
    try:
        graph_data = await graphrag_service.get_graph_by_book(book_id)
        return graph_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图谱失败: {str(e)}")


@router.post("/node/subgraph", response_model=GraphData)
async def get_node_subgraph(request: NodeSubgraphRequest):
    """
    获取以指定节点为中心的子图

    Args:
        request: 节点子图请求

    Returns:
        子图数据
    """
    try:
        subgraph = await graphrag_service.get_node_subgraph(
            node_id=request.node_id,
            book_id=request.book_id,
            depth=request.depth
        )
        return subgraph
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取节点子图失败: {str(e)}")
