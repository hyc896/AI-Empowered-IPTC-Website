# -*- coding: utf-8 -*-

"""
实践方案生成Celery任务
"""

import uuid
from datetime import datetime
from celery_app import celery_app
from database.connection import SessionLocal
from database.entities import PracticePlan, KnowledgePoint, PracticeType
from services.ai_plan_generator import AIPlanGenerator


@celery_app.task(bind=True, name="generate_practice_plan")
def generate_practice_plan_task(
    self,
    user_id: str,
    knowledge_point_id: str,
    practice_type: str,
    preferences: dict = None
):
    """
    生成实践方案的Celery任务

    Args:
        self: Celery任务实例
        user_id: 用户ID
        knowledge_point_id: 知识点ID
        practice_type: 实践类型
        preferences: 用户偏好

    Returns:
        生成的方案ID
    """
    db = SessionLocal()

    try:
        # 创建方案记录（状态为generating）
        plan_id = str(uuid.uuid4())
        plan = PracticePlan(
            id=plan_id,
            user_id=user_id,
            knowledge_point_id=knowledge_point_id,
            practice_type=PracticeType(practice_type),
            title="生成中...",
            content="",
            tasks=[],
            generation_status="generating",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(plan)
        db.commit()

        # 获取知识点
        knowledge_point = db.query(KnowledgePoint).filter(
            KnowledgePoint.id == knowledge_point_id
        ).first()

        if not knowledge_point:
            plan.generation_status = "failed"
            plan.error_message = "知识点不存在"
            db.commit()
            return {"status": "failed", "plan_id": plan_id}

        # 初始化LLM客户端（从一期项目复用）
        # 这里需要根据实际情况导入LLM客户端
        # from llm.global_llm_manager import GlobalLLMManager
        # llm_client = GlobalLLMManager.get_instance().get_chat_client()

        # 临时：使用模拟数据
        class MockLLMClient:
            def chat(self, prompt):
                return '''
                {
                    "title": "参观中共一大会址纪念馆实践方案",
                    "content": "## 实践目标\\n通过参观中共一大会址纪念馆，深入理解中国共产党的诞生历程和初心使命。",
                    "tasks": [
                        {"task": "提前预约参观", "description": "通过官网或公众号预约参观时间", "required": true},
                        {"task": "准备采访提纲", "description": "准备3-5个采访问题", "required": true},
                        {"task": "实地参观", "description": "认真参观展览，拍摄照片", "required": true},
                        {"task": "采访参观者", "description": "采访2-3位参观者", "required": false},
                        {"task": "撰写心得", "description": "撰写不少于800字的参观心得", "required": true}
                    ],
                    "venues": [
                        {"name": "中共一大会址纪念馆", "address": "上海市黄浦区兴业路76号", "description": "中国共产党第一次全国代表大会会址"}
                    ],
                    "estimated_hours": 4,
                    "difficulty": "medium"
                }
                '''

        llm_client = MockLLMClient()

        # 生成方案
        generator = AIPlanGenerator(llm_client)
        plan_data = generator.generate_plan(
            knowledge_point,
            PracticeType(practice_type),
            preferences
        )

        # 更新方案
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

        return {"status": "success", "plan_id": plan_id}

    except Exception as e:
        # 更新失败状态
        if plan:
            plan.generation_status = "failed"
            plan.error_message = str(e)
            db.commit()

        return {"status": "failed", "plan_id": plan_id if plan else None, "error": str(e)}

    finally:
        db.close()
