# -*- coding: utf-8 -*-
"""AI辅助评分服务"""

import json
import logging
from sqlalchemy.orm import Session
from database.entities import PracticeSubmission, PracticePlan, KnowledgePoint

logger = logging.getLogger(__name__)


class AIGradingService:
    """AI辅助评分服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_ai_suggestion(self, submission_id: str) -> dict:
        """获取AI评分建议"""
        submission = self.db.query(PracticeSubmission).filter(
            PracticeSubmission.id == submission_id
        ).first()
        if not submission:
            return {"error": "提交不存在"}

        # 获取关联的方案和知识点
        plan = self.db.query(PracticePlan).filter(PracticePlan.id == submission.plan_id).first()
        knowledge_point = None
        if plan and plan.knowledge_point_id:
            knowledge_point = self.db.query(KnowledgePoint).filter(
                KnowledgePoint.id == plan.knowledge_point_id
            ).first()

        prompt = self._build_grading_prompt(submission, plan, knowledge_point)

        try:
            from services.practice_service import RealLLMClient
            llm = RealLLMClient()
            # Override system message for grading
            import os
            import requests
            headers = {
                "Authorization": f"Bearer {llm.api_key}",
                "Content-Type": "application/json"
            }
            models_to_try = [llm.model] + [m for m in llm.FALLBACK_MODELS if m != llm.model]

            last_err = None
            for model in models_to_try:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "你是一位经验丰富的思政课教师，擅长评价学生的实践作业。请严格按照JSON格式输出评分建议。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1500
                }
                try:
                    logger.info(f"AI评分尝试模型: {model}")
                    resp = requests.post(
                        f"{llm.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=30
                    )
                    resp.raise_for_status()
                    content = resp.json()["choices"][0]["message"]["content"]
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()

                    result = json.loads(content)
                    return {
                        "suggested_score": result.get("score", 80),
                        "suggested_comment": result.get("comment", ""),
                        "dimensions": result.get("dimensions", []),
                        "highlights": result.get("highlights", []),
                        "suggestions": result.get("suggestions", [])
                    }
                except Exception as e:
                    last_err = e
                    logger.warning(f"AI评分模型 {model} 失败: {e}")
                    import time
                    time.sleep(1)

            raise last_err

        except Exception as e:
            logger.error(f"AI评分失败: {e}")
            return {"error": f"AI评分服务暂时不可用: {str(e)}"}

    def _build_grading_prompt(self, submission, plan, knowledge_point) -> str:
        kp_info = ""
        if knowledge_point:
            kp_info = f"关联知识点：{knowledge_point.name}\n知识点描述：{knowledge_point.description or '无'}\n"

        plan_info = ""
        if plan:
            plan_info = f"实践方案标题：{plan.title}\n方案要求：{plan.content[:500] if plan.content else '无'}\n"

        tasks_info = ""
        if plan and plan.tasks:
            tasks_info = "方案任务要求：\n"
            for i, task in enumerate(plan.tasks):
                tasks_info += f"  {i+1}. {task.get('task', '')} - {task.get('description', '')}\n"

        return f"""请对以下学生实践作业进行评分分析，给出评分建议和评语。

{kp_info}
{plan_info}
{tasks_info}

学生提交内容：
标题：{submission.title}
实践类型：{submission.practice_type.value}
实践描述：{submission.content[:1000] if submission.content else '无'}
实践感想：{submission.reflection[:1000] if submission.reflection else '无'}

请从以下维度评分（每个维度0-100分），并给出总分和评语：
1. 内容完整性：是否完成了方案要求的各项任务
2. 思想深度：对知识点的理解和反思深度
3. 实践质量：实践过程的认真程度和成果质量
4. 表达能力：文字表达的清晰度和逻辑性

请严格按以下JSON格式输出：
{{
    "score": 85,
    "comment": "总体评语，2-3句话",
    "dimensions": [
        {{"name": "内容完整性", "score": 90, "comment": "简短评价"}},
        {{"name": "思想深度", "score": 80, "comment": "简短评价"}},
        {{"name": "实践质量", "score": 85, "comment": "简短评价"}},
        {{"name": "表达能力", "score": 85, "comment": "简短评价"}}
    ],
    "highlights": ["亮点1", "亮点2"],
    "suggestions": ["改进建议1", "改进建议2"]
}}"""
