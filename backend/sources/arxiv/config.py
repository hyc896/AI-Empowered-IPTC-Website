# -*- coding: utf-8 -*-

"""arXiv配置定义和验证"""

from pydantic import BaseModel, Field, validator
from typing import List
from .constants import VALID_CATEGORIES


class ArxivConfig(BaseModel):
    """arXiv配置Schema"""
    categories: List[str] = Field(..., min_items=1, description="关注的分类")
    max_results_per_category: int = Field(50, ge=1, le=200, description="每个分类最大抓取数量")
    date_range_days: int = Field(7, ge=1, le=30, description="抓取时间范围（天）")
    summary_length_threshold: int = Field(1000, ge=100, le=5000, description="摘要长度阈值")

    mysql_table: str = "arxiv_messages"
    chroma_collection: str = "arxiv_messages"
    collector_module: str = "backend.services.message.sources.arxiv.collector"
    interval: int = 86400
    api_base_url: str = "http://export.arxiv.org/api/query"
    sort_by: str = "submittedDate"

    @validator('categories')
    def validate_categories(cls, v):
        """验证分类是否有效"""
        invalid = [c for c in v if c not in VALID_CATEGORIES]
        if invalid:
            raise ValueError(f"无效的分类: {', '.join(invalid)}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "categories": ["cs.AI", "cs.LG"],
                "max_results_per_category": 50,
                "date_range_days": 7,
                "summary_length_threshold": 1000
            }
        }


def validate_config(config: dict) -> tuple[bool, str]:
    """验证配置是否有效

    Args:
        config: 配置字典

    Returns:
        (是否有效, 错误信息)
    """
    try:
        ArxivConfig(**config)
        return True, ""
    except Exception as e:
        return False, str(e)
