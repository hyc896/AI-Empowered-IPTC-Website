"""
图数据模型

本模块使用Pydantic定义图数据模型。
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any


class GraphData(BaseModel):
    """图数据模型（用于前端可视化）"""

    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="节点列表")
    links: List[Dict[str, Any]] = Field(default_factory=list, description="边列表")
    categories: List[Dict[str, str]] = Field(default_factory=list, description="分类列表")

    class Config:
        json_schema_extra = {
            "example": {
                "nodes": [
                    {"id": "1", "name": "OpenAI", "category": "Company", "value": 10}
                ],
                "links": [
                    {"source": "1", "target": "2", "value": 1}
                ],
                "categories": [
                    {"name": "Company"}
                ]
            }
        }
