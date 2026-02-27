"""
实体数据模型

本模块使用Pydantic定义实体模型。
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class Entity(BaseModel):
    """实体模型"""

    name: str = Field(..., description="实体名称")
    type: str = Field(..., description="实体类型（Company/Person/Technology等）")
    aliases: List[str] = Field(default_factory=list, description="别名列表")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="属性字典")
    mention_count: int = Field(default=1, description="提及次数")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "OpenAI",
                "type": "Company",
                "aliases": ["Open AI"],
                "attributes": {"country": "美国", "industry": "人工智能"},
                "mention_count": 1
            }
        }
