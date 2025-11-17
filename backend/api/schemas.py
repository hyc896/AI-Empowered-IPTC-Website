# -*- coding: utf-8 -*-

"""
API数据模型定义
使用Pydantic进行数据验证和序列化
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator


class MessageSourceResponse(BaseModel):
    """消息源响应模型"""
    id: str = Field(..., description="消息源ID")
    name: str = Field(..., description="消息源名称")
    adapter_name: str = Field(..., description="适配器名称")
    category: Optional[str] = Field(None, description="业务类别")
    display_name: Optional[str] = Field(None, description="显示名称")
    config: Optional[Dict[str, Any]] = Field(None, description="配置信息")
    is_active: bool = Field(True, description="是否启用")
    last_crawled_at: Optional[datetime] = Field(None, description="最后抓取时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class MessageSourceCreate(BaseModel):
    """创建消息源请求模型"""
    name: str = Field(..., min_length=1, max_length=100, description="消息源名称")
    adapter_name: str = Field(..., min_length=1, max_length=100, description="适配器名称")
    category: Optional[str] = Field(None, max_length=50, description="业务类别")
    display_name: Optional[str] = Field(None, max_length=100, description="显示名称")
    config: Optional[Dict[str, Any]] = Field(None, description="配置信息")
    schedule: Optional[str] = Field(None, max_length=50, description="定时任务cron表达式")
    is_active: bool = Field(True, description="是否启用")

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('消息源名称不能为空')
        return v.strip()

    @validator('adapter_name')
    def validate_adapter_name(cls, v):
        if not v.strip():
            raise ValueError('适配器名称不能为空')
        return v.strip()


class MessageSourceUpdate(BaseModel):
    """更新消息源请求模型"""
    adapter_name: Optional[str] = Field(None, min_length=1, max_length=100, description="适配器名称")
    category: Optional[str] = Field(None, max_length=50, description="业务类别")
    display_name: Optional[str] = Field(None, max_length=100, description="显示名称")
    config: Optional[Dict[str, Any]] = Field(None, description="配置信息")
    schedule: Optional[str] = Field(None, max_length=50, description="定时任务cron表达式")
    is_active: Optional[bool] = Field(None, description="是否启用")


class MessageResponse(BaseModel):
    """消息响应模型"""
    id: str = Field(..., description="消息ID")
    title: str = Field(..., description="消息标题")
    content: str = Field(..., description="消息内容")
    url: Optional[str] = Field(None, description="消息链接")
    published_at: Optional[datetime] = Field(None, description="发布时间")
    provider: Optional[str] = Field(None, description="消息提供方")
    source_name: str = Field(..., description="消息源名称")
    source: str = Field(..., description="数据来源(mysql/chromadb)")
    similarity: Optional[float] = Field(None, description="相似度(仅ChromaDB)")
    distance: Optional[float] = Field(None, description="距离(仅ChromaDB)")
    rrf_score: Optional[float] = Field(None, description="RRF融合分数")

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """搜索请求模型"""
    source_type: Optional[str] = Field(None, description="消息源类型")
    query: str = Field(..., min_length=1, description="搜索关键词")
    time_range: Optional[Dict[str, Any]] = Field(None, description="时间范围")
    limit: int = Field(20, ge=1, le=1000, description="返回结果数量")

    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('搜索关键词不能为空')
        return v.strip()

    @validator('time_range')
    def validate_time_range(cls, v):
        if v is not None:
            if not isinstance(v, dict):
                raise ValueError('时间范围必须是字典类型')
            # 可以添加更多验证逻辑
        return v


class SearchResponse(BaseModel):
    """搜索响应模型"""
    results: List[MessageResponse] = Field(..., description="搜索结果")
    total: int = Field(..., description="结果总数")
    query: str = Field(..., description="搜索关键词")
    search_time: float = Field(..., description="搜索耗时(秒)")


class CollectorStatusResponse(BaseModel):
    """采集器状态响应模型"""
    status: str = Field(..., description="运行状态")
    collectors: List[Dict[str, Any]] = Field(..., description="采集器列表")
    healthy_collectors: int = Field(..., description="健康采集器数量")
    total_collectors: int = Field(..., description="总采集器数量")
    startup_time: Optional[datetime] = Field(None, description="启动时间")


class CollectorStatsResponse(BaseModel):
    """采集器统计响应模型"""
    name: str = Field(..., description="采集器名称")
    success_count: int = Field(..., description="成功次数")
    fail_count: int = Field(..., description="失败次数")
    last_success_time: Optional[datetime] = Field(None, description="最后成功时间")
    last_fail_time: Optional[datetime] = Field(None, description="最后失败时间")
    last_error: Optional[str] = Field(None, description="最后错误")
    start_time: Optional[datetime] = Field(None, description="启动时间")
    total_runtime: float = Field(..., description="总运行时间(秒)")


class CollectorActionResponse(BaseModel):
    """采集器操作响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作结果消息")
    timestamp: datetime = Field(default_factory=datetime.now, description="操作时间")


class StatsResponse(BaseModel):
    """统计信息响应模型"""
    sources: Dict[str, int] = Field(..., description="消息源统计")
    messages: Dict[str, int] = Field(..., description="消息统计")
    recent_messages: Dict[str, int] = Field(..., description="最近消息统计")
    total_sources: int = Field(..., description="总消息源数")
    total_messages: int = Field(..., description="总消息数")
    recent_total: int = Field(..., description="最近消息总数")


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    timestamp: float = Field(..., description="时间戳")
    uptime_seconds: Optional[float] = Field(None, description="运行时间")
    database: Dict[str, Any] = Field(..., description="数据库状态")
    collectors: Optional[Dict[str, Any]] = Field(None, description="采集器状态")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.now, description="错误时间")


class SuccessResponse(BaseModel):
    """成功响应模型"""
    success: bool = Field(True, description="操作成功")
    message: str = Field(..., description="成功消息")
    data: Optional[Dict[str, Any]] = Field(None, description="返回数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")


# 分页相关模型
class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=1000, description="每页大小")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class PaginatedResponse(BaseModel):
    """分页响应基类"""
    items: List[Any] = Field(..., description="数据项")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")

    @classmethod
    def create(cls, items: List[Any], total: int, pagination: PaginationParams):
        """创建分页响应"""
        pages = (total + pagination.size - 1) // pagination.size
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=pages
        )


# 地理统计相关模型
class GeoStatisticsResponse(BaseModel):
    """地理统计响应模型"""
    statistics: Dict[str, int] = Field(..., description="各国家/地区的消息数量统计（中文国家名作为key）")
    total_messages: int = Field(..., description="消息总数")
    total_countries: int = Field(..., description="国家总数")
    filters_applied: Dict[str, Any] = Field(..., description="应用的筛选条件")


class RegionMessagesResponse(BaseModel):
    """地区消息列表响应模型"""
    items: List[Dict[str, Any]] = Field(..., description="消息列表")
    total: int = Field(..., description="总数量")
    limit: int = Field(..., description="返回数量限制")
    offset: int = Field(..., description="偏移量")
    region: str = Field(..., description="查询的地区名")


# AI日报相关模型
class AIDailyReportResponse(BaseModel):
    """AI日报响应模型"""
    id: str = Field(..., description="报告ID")
    report_date: str = Field(..., description="报告日期（YYYY-MM-DD）")
    content: str = Field(..., description="报告内容（Markdown格式）")
    statistics: Dict[str, Any] = Field(..., description="统计数据")
    governance_count: int = Field(..., description="AI治理信息数量")
    research_count: int = Field(..., description="AI科研信息数量")
    industry_count: int = Field(..., description="AI产业信息数量")
    total_messages: int = Field(..., description="消息总数")
    generation_status: str = Field(..., description="生成状态（pending/completed/failed）")
    error_message: Optional[str] = Field(None, description="错误信息")
    generated_at: datetime = Field(..., description="生成时间")
    model_version: str = Field(..., description="模型版本")

    class Config:
        from_attributes = True


class AIDailyReportListResponse(BaseModel):
    """AI日报列表响应模型"""
    items: List[AIDailyReportResponse] = Field(..., description="报告列表")
    total: int = Field(..., description="总数量")
    limit: int = Field(..., description="返回数量限制")
    offset: int = Field(..., description="偏移量")


# 类型别名
MessageSourceList = List[MessageSourceResponse]
MessageList = List[MessageResponse]
CollectorList = List[CollectorStatsResponse]