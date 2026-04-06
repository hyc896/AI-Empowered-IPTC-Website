# -*- coding: utf-8 -*-

"""
实践方案服务
"""

import uuid
import os
import json
import logging
import threading
from datetime import datetime
from typing import Optional
from pathlib import Path
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from dotenv import load_dotenv

from database.entities import PracticePlan, KnowledgePoint, User, PracticeType
from database.connection import SessionLocal
from schemas.practice import (
    PracticePlanGenerateRequest,
    PracticePlanGenerateResponse,
    TaskStatusResponse,
    PracticePlanResponse,
    PracticePlanListResponse,
    FreePlanCreateRequest
)
from services.ai_plan_generator import AIPlanGenerator

# 加载环境变量
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / "config" / ".env")

logger = logging.getLogger(__name__)


class RealLLMClient:
    """LLM客户端（DeepSeek官方API）"""

    # DeepSeek官方API仅支持自家模型，无需降级列表
    FALLBACK_MODELS = [
        "deepseek-chat",
    ]

    def __init__(self):
        import requests
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
        self.model = os.getenv("LLM_MODEL", "deepseek-chat")
        self.requests = requests

    def chat(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 构建尝试列表：先用配置的模型，再按降级列表
        models_to_try = [self.model] + [m for m in self.FALLBACK_MODELS if m != self.model]

        last_err = None
        for model in models_to_try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是一位资深的高校思政课实践教学设计专家，拥有10年以上的教学经验。你的方案必须具有高度可操作性，让学生看完就能执行。描述步骤时请使用自然流畅的语言，像面对面指导学生一样，不要使用'做什么：''怎么做：'等生硬的标签格式。请严格按照JSON格式输出，不要输出任何其他内容。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 3000
            }
            try:
                logger.info(f"尝试模型: {model}")
                resp = self.requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                logger.info(f"模型 {model} 调用成功")
                return content
            except Exception as e:
                last_err = e
                logger.warning(f"模型 {model} 调用失败: {e}")
                import time
                time.sleep(1)

        raise last_err


def _generate_in_background(plan_id: str, knowledge_point_name: str, knowledge_point_description: str, knowledge_point_keywords: str, practice_type_value: str, preferences: dict):
    """后台线程：调用LLM生成方案并写入数据库"""
    db = SessionLocal()
    try:
        plan = db.query(PracticePlan).filter(PracticePlan.id == plan_id).first()
        if not plan:
            return

        llm_client = RealLLMClient()
        generator = AIPlanGenerator(llm_client)

        class KPProxy:
            pass
        kp = KPProxy()
        kp.name = knowledge_point_name
        kp.description = knowledge_point_description
        kp.keywords = knowledge_point_keywords

        plan_data = generator.generate_plan(
            kp,
            PracticeType(practice_type_value),
            preferences
        )

        plan.title = plan_data.get("title", "实践方案")
        plan.content = plan_data.get("content", "")
        plan.tasks = plan_data.get("tasks", [])
        plan.venues = plan_data.get("venues", [])
        plan.estimated_hours = plan_data.get("estimated_hours", 4)
        plan.difficulty = plan_data.get("difficulty", "medium")
        plan.generation_status = "success"
        plan.generated_at = datetime.now()
        plan.updated_at = datetime.now()
        db.commit()
        logger.info(f"方案生成成功: {plan_id}")

    except Exception as e:
        logger.error(f"方案生成失败: {plan_id}: {e}")
        try:
            plan = db.query(PracticePlan).filter(PracticePlan.id == plan_id).first()
            if plan:
                plan.generation_status = "failed"
                plan.error_message = str(e)
                plan.updated_at = datetime.now()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


class PracticeService:
    """实践方案服务类"""

    def __init__(self, db: Session):
        self.db = db

    def generate_plan(self, user: User, request: PracticePlanGenerateRequest) -> PracticePlanGenerateResponse:
        """创建方案记录，后台线程调用LLM，立即返回task_id"""
        knowledge_point = self.db.query(KnowledgePoint).filter(
            KnowledgePoint.id == request.knowledge_point_id
        ).first()

        if not knowledge_point:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识点不存在")

        plan_id = str(uuid.uuid4())
        preferences = request.preferences or {}
        if request.venue_id:
            preferences = {**preferences, "venue_id": request.venue_id}
        # 注入学生个人信息，用于AI生成更精准的方案
        if user.major:
            preferences["student_major"] = user.major
        if user.interests:
            preferences["student_interests"] = user.interests

        plan = PracticePlan(
            id=plan_id,
            user_id=user.id,
            knowledge_point_id=request.knowledge_point_id,
            practice_type=PracticeType(request.practice_type),
            title="生成中...",
            content="",
            tasks=[],
            venue_id=request.venue_id,
            generation_status="generating",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.db.add(plan)
        self.db.commit()

        # 后台线程生成，不阻塞请求
        thread = threading.Thread(
            target=_generate_in_background,
            args=(
                plan_id,
                knowledge_point.name,
                knowledge_point.description or '',
                knowledge_point.keywords or '',
                request.practice_type,
                preferences
            ),
            daemon=True
        )
        thread.start()

        return PracticePlanGenerateResponse(
            task_id=plan_id,
            status="generating",
            estimated_time=30
        )

    def get_task_status(self, task_id: str) -> TaskStatusResponse:
        """用 plan_id 直接查数据库状态，不依赖 Celery"""
        plan = self.db.query(PracticePlan).filter(PracticePlan.id == task_id).first()

        if not plan:
            return TaskStatusResponse(task_id=task_id, status="pending")

        if plan.generation_status == "success":
            return TaskStatusResponse(
                task_id=task_id,
                status="success",
                plan=PracticePlanResponse.from_orm(plan)
            )
        elif plan.generation_status == "failed":
            return TaskStatusResponse(
                task_id=task_id,
                status="failed",
                error_message=plan.error_message or "生成失败"
            )
        else:
            return TaskStatusResponse(task_id=task_id, status="generating")

    def get_plan(self, plan_id: str, user: User) -> PracticePlanResponse:
        from sqlalchemy.orm import joinedload
        plan = self.db.query(PracticePlan).options(joinedload(PracticePlan.knowledge_point)).filter(PracticePlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="方案不存在")
        if plan.user_id != user.id and user.role.value not in ["teacher", "admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看此方案")
        return PracticePlanResponse.from_orm(plan)

    def list_my_plans(self, user: User, practice_type: Optional[str] = None, page: int = 1, page_size: int = 20) -> PracticePlanListResponse:
        from database.entities import PracticeSubmission, SubmissionStatus
        from sqlalchemy import and_, not_, exists
        from sqlalchemy.orm import joinedload

        query = self.db.query(PracticePlan).options(joinedload(PracticePlan.knowledge_point)).filter(PracticePlan.user_id == user.id)
        if practice_type:
            query = query.filter(PracticePlan.practice_type == practice_type)

        # 只显示尚未真正提交过的方案（排除有非草稿状态 submission 的方案）
        has_submitted = exists().where(
            and_(
                PracticeSubmission.plan_id == PracticePlan.id,
                PracticeSubmission.status != SubmissionStatus.DRAFT
            )
        )
        query = query.filter(not_(has_submitted))

        total = query.count()
        items = query.order_by(PracticePlan.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return PracticePlanListResponse(total=total, items=[PracticePlanResponse.from_orm(i) for i in items])

    def delete_plan(self, plan_id: str, user: User) -> dict:
        plan = self.db.query(PracticePlan).filter(PracticePlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="方案不存在")
        if plan.user_id != user.id and user.role.value != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除此方案")

        # 先删除关联的提交及其子记录（审核记录、批注），避免外键约束报错
        from database.entities import PracticeSubmission, PracticeReview, SubmissionAnnotation
        submissions = self.db.query(PracticeSubmission).filter(PracticeSubmission.plan_id == plan_id).all()
        for sub in submissions:
            # 删除批注
            self.db.query(SubmissionAnnotation).filter(SubmissionAnnotation.submission_id == sub.id).delete()
            # 删除审核记录
            self.db.query(PracticeReview).filter(PracticeReview.submission_id == sub.id).delete()
            # 删除提交本身
            self.db.delete(sub)

        self.db.delete(plan)
        self.db.commit()
        return {"message": "方案删除成功"}

    def set_deadline(self, plan_id: str, deadline: str, user: User) -> dict:
        from datetime import datetime
        plan = self.db.query(PracticePlan).filter(PracticePlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="方案不存在")
        if plan.user_id != user.id and user.role.value != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改此方案")
        plan.deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
        self.db.commit()
        return {"message": "截止日期已设置"}

    def create_free_plan(self, user: User, request: FreePlanCreateRequest) -> PracticePlanResponse:
        """学生自主创建自由申请方案，不调用AI，直接创建方案+草稿提交"""
        knowledge_point = self.db.query(KnowledgePoint).filter(
            KnowledgePoint.id == request.knowledge_point_id
        ).first()
        if not knowledge_point:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识点不存在")

        content_parts = [f"## 实践背景\n{request.description}"]
        if request.expected_outcome:
            content_parts.append(f"## 预期成果\n{request.expected_outcome}")

        plan = PracticePlan(
            id=str(uuid.uuid4()),
            user_id=user.id,
            knowledge_point_id=request.knowledge_point_id,
            practice_type=PracticeType.FREE,
            title=request.title,
            content="\n\n".join(content_parts),
            tasks=[{"task": "完成自定义实践", "description": request.description, "required": True, "submission_requirements": []}],
            venues=[],
            venue_id=request.venue_id or None,
            estimated_hours=4,
            difficulty="medium",
            generation_status="success",
            generated_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.db.add(plan)
        self.db.flush()

        # 同时创建草稿提交记录，含用户填写的基本信息
        from database.entities import PracticeSubmission, SubmissionStatus
        from datetime import datetime as dt

        completion_date = None
        if request.completion_date:
            try:
                completion_date = dt.fromisoformat(request.completion_date)
            except Exception:
                pass

        submission = PracticeSubmission(
            id=str(uuid.uuid4()),
            plan_id=plan.id,
            user_id=user.id,
            practice_type=PracticeType.FREE,
            title=request.title,
            content=json.dumps([[""]]),
            result_form=request.result_form or "",
            class_name_id=request.class_name_id or "",
            showcase_preference=request.showcase_preference or "original",
            instructor_name=request.instructor_name or "",
            completion_date=completion_date,
            venue_id=request.venue_id or None,
            status=SubmissionStatus.DRAFT,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.db.add(submission)
        self.db.commit()
        self.db.refresh(plan)
        return PracticePlanResponse.from_orm(plan)
