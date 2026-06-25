# -*- coding: utf-8 -*-
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import httpx

from database import get_db
from database.entities import User, UserRole, PracticePlan, PracticeSubmission, Venue, KnowledgePoint
from api.auth_routes import get_current_user

router = APIRouter()
COLLECTOR_URL = os.getenv("COLLECTOR_URL", "http://collector-backend:11528").rstrip("/")


def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    return current_user


@router.get("/overview")
def get_overview(db: Session = Depends(get_db), _=Depends(require_admin)):
    return {
        "submission_count": db.query(func.count(PracticeSubmission.id)).scalar() or 0,
        "user_count": db.query(func.count(User.id)).scalar() or 0,
        "plan_count": db.query(func.count(PracticePlan.id)).scalar() or 0,
        "venue_count": db.query(func.count(Venue.id)).scalar() or 0,
        "knowledge_point_count": db.query(func.count(KnowledgePoint.id)).scalar() or 0,
    }


@router.get("/message-sources")
async def get_message_sources(_=Depends(require_admin)):
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{COLLECTOR_URL}/api/v1/collection/status")
            return r.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"无法连接采集服务: {e}")


@router.get("/collectors")
async def get_collectors(_=Depends(require_admin)):
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{COLLECTOR_URL}/api/v1/collectors/list")
            return r.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"无法连接采集服务: {e}")


@router.post("/collectors/{source_name}/trigger")
async def trigger_collector(source_name: str, _=Depends(require_admin)):
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.post(f"{COLLECTOR_URL}/api/v1/collectors/{source_name}/trigger")
            return r.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"触发采集失败: {e}")


@router.post("/trigger-matching")
async def trigger_matching(_=Depends(require_admin)):
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.post(f"{COLLECTOR_URL}/api/v1/iptc/trigger-matching")
            return r.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"触发失败: {e}")


@router.post("/trigger-case-generation")
async def trigger_case_generation(_=Depends(require_admin)):
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.post(f"{COLLECTOR_URL}/api/v1/iptc/trigger-case-generation")
            return r.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"触发失败: {e}")


@router.get("/matching-status")
async def get_matching_status(_=Depends(require_admin)):
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{COLLECTOR_URL}/api/v1/collection/matching-status")
            return r.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"无法连接采集服务: {e}")


@router.get("/users")
def get_users(page: int = 1, page_size: int = 20, db: Session = Depends(get_db), _=Depends(require_admin)):
    offset = (page - 1) * page_size
    total = db.query(func.count(User.id)).scalar()
    users = db.query(User).offset(offset).limit(page_size).all()
    return {
        "total": total,
        "items": [{"id": u.id, "username": u.username, "real_name": u.real_name,
                   "role": u.role.value, "is_active": u.is_active,
                   "created_at": u.created_at.isoformat() if u.created_at else None} for u in users]
    }


@router.put("/users/{user_id}/role")
def update_user_role(user_id: str, role: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    try:
        user.role = UserRole(role)
        db.commit()
        return {"success": True}
    except ValueError:
        raise HTTPException(status_code=400, detail="无效角色")


@router.get("/practices")
def get_practices(page: int = 1, page_size: int = 20, db: Session = Depends(get_db), _=Depends(require_admin)):
    offset = (page - 1) * page_size
    total = db.query(func.count(PracticeSubmission.id)).scalar()
    items = db.query(PracticeSubmission).offset(offset).limit(page_size).all()
    return {
        "total": total,
        "items": [{"id": s.id, "title": s.title,
                   "status": s.status.value if s.status else None,
                   "created_at": s.created_at.isoformat() if s.created_at else None} for s in items]
    }


@router.get("/venues")
def get_venues(db: Session = Depends(get_db), _=Depends(require_admin)):
    total = db.query(func.count(Venue.id)).scalar()
    verified = db.query(func.count(Venue.id)).filter(Venue.is_verified == True).scalar()
    return {"total": total, "verified": verified, "unverified": total - verified}
