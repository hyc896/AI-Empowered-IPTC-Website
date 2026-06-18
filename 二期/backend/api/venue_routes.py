# -*- coding: utf-8 -*-

"""
场馆相关API路由
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from database import get_db
from database.entities import Venue
from api.auth_routes import get_current_user

router = APIRouter()


class VenueResponse(BaseModel):
    id: str
    name: str
    category: Optional[str] = None
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    opening_hours: Optional[str] = None
    contact_phone: Optional[str] = None
    official_website: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    related_knowledge_points: Optional[list] = None
    images: Optional[list] = None
    is_verified: bool = False
    is_active: bool = True

    class Config:
        from_attributes = True


class VenueCreate(BaseModel):
    name: str
    category: Optional[str] = None
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    opening_hours: Optional[str] = None
    contact_phone: Optional[str] = None
    official_website: Optional[str] = None
    source_url: Optional[str] = None


class VenueUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    opening_hours: Optional[str] = None
    contact_phone: Optional[str] = None
    official_website: Optional[str] = None
    source_url: Optional[str] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None


class VenueListResponse(BaseModel):
    total: int
    items: List[VenueResponse]


class VenueCategoryCount(BaseModel):
    category: str
    count: int


class VenueRegionCount(BaseModel):
    region: str
    count: int


@router.get("", response_model=VenueListResponse, summary="获取场馆列表")
def list_venues(
    category: Optional[str] = Query(None, description="场馆类别"),
    keyword: Optional[str] = Query(None, description="搜索关键词（名称/地址）"),
    region: Optional[str] = Query(None, description="地区筛选（从地址中匹配）"),
    source: Optional[str] = Query(None, description="来源筛选（红途/手动）"),
    knowledge_point_id: Optional[str] = Query(None, description="关联知识点ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Venue).filter(Venue.is_active == True)
    if category:
        query = query.filter(Venue.category == category)
    if keyword:
        query = query.filter(
            (Venue.name.contains(keyword)) | (Venue.address.contains(keyword))
        )
    if region:
        query = query.filter(Venue.address.contains(region))
    if source:
        query = query.filter(Venue.source == source)
    if knowledge_point_id:
        # related_knowledge_points 是 JSON 数组，使用 JSON_CONTAINS 查询
        query = query.filter(
            Venue.related_knowledge_points.op("LIKE")(f'%"{knowledge_point_id}"%')
        )
    total = query.count()
    items = query.order_by(Venue.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return VenueListResponse(total=total, items=items)


@router.get("/categories", summary="获取场馆类别列表")
def list_categories(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    region: Optional[str] = Query(None, description="地区筛选"),
    source: Optional[str] = Query(None, description="来源筛选"),
    knowledge_point_id: Optional[str] = Query(None, description="关联知识点ID"),
    db: Session = Depends(get_db)
):
    """获取所有场馆类别及数量（支持按当前筛选条件动态计算）"""
    from sqlalchemy import func
    query = db.query(Venue.category, func.count(Venue.id)).filter(
        Venue.is_active == True, Venue.category != None
    )
    if keyword:
        query = query.filter(
            (Venue.name.contains(keyword)) | (Venue.address.contains(keyword))
        )
    if region:
        query = query.filter(Venue.address.contains(region))
    if source:
        query = query.filter(Venue.source == source)
    if knowledge_point_id:
        query = query.filter(
            Venue.related_knowledge_points.op("LIKE")(f'%"{knowledge_point_id}"%')
        )
    results = (
        query.group_by(Venue.category)
        .order_by(func.count(Venue.id).desc())
        .all()
    )
    return [VenueCategoryCount(category=cat, count=cnt) for cat, cnt in results if cat]


@router.get("/regions", summary="获取场馆地区列表")
def list_regions(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    category: Optional[str] = Query(None, description="场馆类别"),
    source: Optional[str] = Query(None, description="来源筛选"),
    knowledge_point_id: Optional[str] = Query(None, description="关联知识点ID"),
    db: Session = Depends(get_db)
):
    """从地址中提取区域信息（上海各区），支持按当前筛选条件动态计算"""
    query = db.query(Venue.address).filter(Venue.is_active == True)
    if keyword:
        query = query.filter(
            (Venue.name.contains(keyword)) | (Venue.address.contains(keyword))
        )
    if category:
        query = query.filter(Venue.category == category)
    if source:
        query = query.filter(Venue.source == source)
    if knowledge_point_id:
        query = query.filter(
            Venue.related_knowledge_points.op("LIKE")(f'%"{knowledge_point_id}"%')
        )
    venues = query.all()
    region_counts = {}
    shanghai_districts = [
        "黄浦区", "徐汇区", "长宁区", "静安区", "普陀区", "虹口区", "杨浦区",
        "闵行区", "宝山区", "嘉定区", "浦东新区", "金山区", "松江区", "青浦区",
        "奉贤区", "崇明区"
    ]
    for (addr,) in venues:
        if not addr:
            continue
        matched = False
        for district in shanghai_districts:
            if district in addr:
                region_counts[district] = region_counts.get(district, 0) + 1
                matched = True
                break
        if not matched:
            # 尝试提取省市
            if "上海" in addr:
                region_counts["上海（其他）"] = region_counts.get("上海（其他）", 0) + 1
            else:
                region_counts["其他地区"] = region_counts.get("其他地区", 0) + 1

    results = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)
    return [VenueRegionCount(region=r, count=c) for r, c in results]


@router.get("/{venue_id}", response_model=VenueResponse, summary="获取场馆详情")
def get_venue(
    venue_id: str,
    db: Session = Depends(get_db)
):
    venue = db.query(Venue).filter(Venue.id == venue_id, Venue.is_active == True).first()
    if not venue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场馆不存在")
    return venue


@router.post("", response_model=VenueResponse, summary="新建场馆（教师/管理员）")
def create_venue(
    data: VenueCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.value not in ["admin", "teacher"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    import uuid as _uuid
    venue = Venue(
        id=str(_uuid.uuid4()),
        name=data.name,
        category=data.category,
        address=data.address or "",
        latitude=data.latitude,
        longitude=data.longitude,
        description=data.description,
        opening_hours=data.opening_hours,
        contact_phone=data.contact_phone,
        official_website=data.official_website,
        source="手动",
        source_url=data.source_url,
        is_verified=True,
        is_active=True,
    )
    db.add(venue)
    db.commit()
    db.refresh(venue)
    return venue


@router.put("/{venue_id}", response_model=VenueResponse, summary="编辑场馆（教师/管理员）")
def update_venue(
    venue_id: str,
    data: VenueUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.value not in ["admin", "teacher"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场馆不存在")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(venue, field, value)
    db.commit()
    db.refresh(venue)
    return venue


@router.delete("/{venue_id}", summary="删除场馆（软删除，教师/管理员）")
def delete_venue(
    venue_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.value not in ["admin", "teacher"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场馆不存在")
    venue.is_active = False
    db.commit()
    return {"message": "场馆已删除"}


