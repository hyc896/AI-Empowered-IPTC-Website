"""
关系数据模型

本模块使用Pydantic定义关系模型。
"""

from pydantic import BaseModel, Field
from typing import Dict, Any


class Relation(BaseModel):
    """关系模型"""

    source: str = Field(..., description="源实体名称")
    target: str = Field(..., description="目标实体名称")
    type: str = Field(..., description="关系类型（WORKS_AT/INVESTS_IN等）")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系属性")

    class Config:
        json_schema_extra = {
            "example": {
                "source": "Sam Altman",
                "target": "OpenAI",
                "type": "WORKS_AT",
                "properties": {"role": "CEO"}
            }
        }
