"""
Pydantic 数据模型定义
定义 API 请求和响应的数据结构
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============ 文件上传相关模型 ============

class UploadResponse(BaseModel):
    """文件上传响应"""
    file_id: str = Field(..., description="文件唯一标识")
    filename: str = Field(..., description="文件名")
    total_pages: int = Field(..., description="PDF 总页数")
    current_range: str = Field(..., description="当前页面范围，如 '1-20'")
    text: str = Field(..., description="提取的文本内容")
    char_count: int = Field(..., description="字符数")


class PageRangeRequest(BaseModel):
    """页面范围请求"""
    page_start: int = Field(1, ge=1, description="起始页码")
    page_end: int = Field(20, ge=1, description="结束页码")


# ============ 实体提取相关模型 ============

class EntityAttribute(BaseModel):
    """实体属性"""
    key: str
    value: str


class Entity(BaseModel):
    """实体模型"""
    name: str = Field(..., description="实体名称")
    type: str = Field(..., description="实体类型")
    aliases: List[str] = Field(default_factory=list, description="别名列表")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="属性字典")
    mention_count: int = Field(1, description="提及次数")


class Relation(BaseModel):
    """关系模型"""
    source: str = Field(..., description="源实体名称")
    target: str = Field(..., description="目标实体名称")
    type: str = Field(..., description="关系类型")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系属性")


class ExtractRequest(BaseModel):
    """实体提取请求"""
    file_id: str = Field(..., description="文件 ID")
    filename: str = Field(..., description="文件名")
    text: str = Field(..., description="待提取的文本内容")
    language: str = Field("zh", description="语言，zh 或 en")
    page_range: Optional[str] = Field(None, description="页面范围，如 '1-20'")


class ExtractResponse(BaseModel):
    """实体提取响应"""
    entities: List[Entity] = Field(..., description="提取的实体列表")
    relations: List[Relation] = Field(..., description="提取的关系列表")
    stats: Dict[str, int] = Field(..., description="统计信息")


# ============ 图谱可视化相关模型 ============

class GraphNode(BaseModel):
    """图谱节点"""
    id: str = Field(..., description="节点 ID")
    name: str = Field(..., description="节点名称")
    category: str = Field(..., description="节点类别")
    value: int = Field(1, description="节点权重")
    symbolSize: int = Field(30, description="节点大小")


class GraphLink(BaseModel):
    """图谱边"""
    source: str = Field(..., description="源节点 ID")
    target: str = Field(..., description="目标节点 ID")
    value: int = Field(1, description="边权重")
    label: str = Field(..., description="关系类型标签")


class GraphCategory(BaseModel):
    """图谱类别"""
    name: str = Field(..., description="类别名称")


class GraphData(BaseModel):
    """图谱可视化数据"""
    nodes: List[GraphNode] = Field(..., description="节点列表")
    links: List[GraphLink] = Field(..., description="边列表")
    categories: List[GraphCategory] = Field(..., description="类别列表")


# ============ 历史记录相关模型 ============

class HistoryItem(BaseModel):
    """历史记录项"""
    id: str = Field(..., description="历史记录 ID")
    file_id: str = Field(..., description="文件 ID")
    filename: str = Field(..., description="文件名")
    page_range: str = Field(..., description="页面范围")
    processed_at: str = Field(..., description="处理时间")
    entity_count: int = Field(..., description="实体数量")
    relation_count: int = Field(..., description="关系数量")


class HistoryDetail(HistoryItem):
    """历史记录详情"""
    entities: List[Entity] = Field(..., description="实体列表")
    relations: List[Relation] = Field(..., description="关系列表")


class HistoryListResponse(BaseModel):
    """历史记录列表响应"""
    items: List[HistoryItem] = Field(..., description="历史记录列表")
    total: int = Field(..., description="总数")


# ============ 导出相关模型 ============

class ExportRequest(BaseModel):
    """导出请求"""
    file_id: str = Field(..., description="文件 ID")
    format: str = Field("json", description="导出格式：json 或 csv")
    include_graph: bool = Field(False, description="是否包含图谱数据")


class RenameRequest(BaseModel):
    """重命名请求"""
    new_name: str = Field(..., description="新文件名")


# ============ 书籍知识图谱相关模型 ============

class BookInfo(BaseModel):
    """书籍信息"""
    book_id: str = Field(..., description="书籍ID（文件ID）")
    book_name: str = Field(..., description="书籍名称")
    upload_time: str = Field(..., description="上传时间")
    entity_count: int = Field(0, description="实体数量")
    relation_count: int = Field(0, description="关系数量")


class BookListResponse(BaseModel):
    """书籍列表响应"""
    books: List[BookInfo] = Field(..., description="书籍列表")
    total: int = Field(..., description="总数")


class NodeSubgraphRequest(BaseModel):
    """节点子图请求"""
    node_id: str = Field(..., description="节点ID（实体名称）")
    book_id: Optional[str] = Field(None, description="书籍ID（可选）")
    depth: int = Field(1, ge=1, le=3, description="扩展深度，1-3层")
