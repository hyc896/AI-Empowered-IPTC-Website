# -*- coding: utf-8 -*-

"""
AI实践方案生成服务
"""

import json
from typing import Dict, Any
from database.entities import KnowledgePoint, PracticeType


# 难度配置
DIFFICULTY_CONFIG = {
    "easy": {
        "label": "简单",
        "hours": "2-3小时",
        "steps": "3-4",
        "depth": "基础了解，完成基本任务即可",
        "output": "简短文字记录或1-2张照片",
        "individual_note": "适合个人独立完成，步骤清晰，材料易获取，无需外出或仅需短途",
        "group_note": "适合2-3人小组，分工简单，每人负责1个步骤",
    },
    "medium": {
        "label": "中等",
        "hours": "4-6小时",
        "steps": "5-6",
        "depth": "有一定深度，需要调研和思考",
        "output": "调研记录、多张照片或短视频",
        "individual_note": "适合个人完成，需要一定时间投入，可能需要外出调研",
        "group_note": "适合3-5人团队，分工明确，各有侧重，成果需整合",
    },
    "hard": {
        "label": "困难",
        "hours": "8小时以上",
        "steps": "6-8",
        "depth": "深度分析，需要多方资源整合，成果质量要求高",
        "output": "完整报告、视频作品或系统性成果",
        "individual_note": "对个人要求较高，需要较强的自主学习和执行能力",
        "group_note": "强烈推荐团队完成，需要精细分工，各成员发挥专长，最终整合高质量成果",
    }
}


class AIPlanGenerator:
    """AI实践方案生成器"""

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def generate_plan(
        self,
        knowledge_point,
        practice_type: PracticeType,
        preferences: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        prompt = self._build_prompt(knowledge_point, practice_type, preferences)
        response = self.llm_client.chat(prompt)
        return self._parse_response(response, practice_type)

    def _build_prompt(self, knowledge_point, practice_type: PracticeType, preferences: Dict[str, Any] = None) -> str:
        prefs = preferences or {}
        location = prefs.get("location", "上海")
        difficulty = prefs.get("difficulty", "easy")
        mode = prefs.get("mode", "individual")
        group_division = prefs.get("group_division", "")

        diff = DIFFICULTY_CONFIG.get(difficulty, DIFFICULTY_CONFIG["easy"])
        is_group = mode == "group"

        mode_label = "集体完成" if is_group else "个人完成"
        mode_note = diff["group_note"] if is_group else diff["individual_note"]
        group_division_note = f"\n团队分工说明（学生填写）：{group_division}" if is_group and group_division else ""

        base_context = f"""知识点：{knowledge_point.name}
知识点描述：{knowledge_point.description or '无'}
关键词：{knowledge_point.keywords or '无'}
地点偏好：{location}
完成方式：{mode_label}
难度等级：{diff['label']}（{diff['hours']}）{group_division_note}"""

        # 学生个人信息（如有）
        student_major = prefs.get("student_major", "")
        student_interests = prefs.get("student_interests", "")
        if student_major or student_interests:
            student_profile = "\n\n学生个人信息："
            if student_major:
                student_profile += f"\n专业：{student_major}"
            if student_interests:
                student_profile += f"\n兴趣特长：{student_interests}"
            student_profile += "\n请根据学生的专业背景和兴趣特长，设计更贴合其专业方向的实践方案。例如法学专业可侧重法治实践，传播专业可侧重媒体创作，社会学专业可侧重社会调研。"
            base_context += student_profile

        difficulty_rules = f"""
难度设计要求（必须严格遵守）：
- 难度等级：{diff['label']}，预计耗时 {diff['hours']}
- 步骤数量：{diff['steps']} 个步骤
- 深度要求：{diff['depth']}
- 成果要求：{diff['output']}
- 完成方式说明：{mode_note}
- 方案的实际难度必须与"{diff['label']}"等级相符，不能虚高或虚低
- 在JSON的difficulty字段中必须填写："{difficulty}"（easy/medium/hard之一）"""

        group_rules = ""
        if is_group:
            group_rules = f"""
集体完成专项要求：
- 每个步骤必须明确标注"负责人"或"分工建议"（如：全员参与 / 组长负责 / 各自完成后汇总）
- 设计需要协作才能完成的环节，体现团队价值
- 最终成果要求体现团队整体水平，而非个人拼凑"""

        common_rules = f"""
通用要求（必须严格遵守）：
1. 方案标题必须具体且吸引人，体现知识点核心概念，不超过30字
2. content字段使用Markdown格式，包含：实践背景、实践目标、预期成果三个部分
3. 每个步骤的description用自然流畅的语言描述，像老师面对面指导，100字以上，避免"做什么：""怎么做："等生硬标签
4. submission_requirements的type只能是photo/video/audio/document/text/url之一
5. 方案必须具有可操作性，学生看完就能动手执行
6. 所有推荐场馆/地点必须真实存在，提供准确地址
7. 步骤之间要有逻辑递进关系{group_rules}"""

        json_format = """{
    "title": "方案标题（具体生动，不超过30字）",
    "content": "## 实践背景\\n...\\n## 实践目标\\n...\\n## 预期成果\\n...",
    "tasks": [
        {
            "task": "步骤名称（动词开头）",
            "description": "自然流畅地描述这一步要做的事，100字以上",
            "required": true,
            "submission_requirements": [
                {"type": "photo", "description": "具体要拍什么"},
                {"type": "text", "description": "具体要写什么", "min_words": 100}
            ]
        }
    ],
    "venues": [
        {"name": "场馆名称", "address": "详细地址（精确到街道门牌号）", "phone": "联系电话", "description": "与知识点的关联及实践建议"}
    ],
    "estimated_hours": 3,
    "difficulty": "easy"
}"""

        if practice_type == PracticeType.VISIT:
            return f"""你是一位经验丰富的高校思政课实践教学设计专家。

请为大学生设计一个【参观研学类】实践方案。

{base_context}

{difficulty_rules}

具体要求：
1. 推荐1-3个{location}地区的真实场馆（博物馆、纪念馆、红色景点等），确保地址真实准确
2. 每个场馆说明与知识点"{knowledge_point.name}"的具体关联
3. 步骤包含：行前资料研读→实地观察记录→重点展区深度学习→（可选）与工作人员交流→个人/团队反思总结
4. 步骤具体到"在XX展厅观察XX，记录XX"、"就XX问题向讲解员提问"
5. 简单难度：1个场馆，基础参观记录；中等：2个场馆，有深度思考；困难：多场馆对比研究，形成完整报告

{common_rules}

请以JSON格式输出：
{json_format}"""

        elif practice_type == PracticeType.PERFORMANCE:
            return f"""你是一位经验丰富的高校思政课实践教学设计专家。

请为大学生设计一个【表演体验类】实践方案。

{base_context}

{difficulty_rules}

具体要求：
1. 设计具体表演形式：情景剧、朗诵、话剧、角色扮演、演讲等
2. 提供内容框架：主题定位、角色设定、核心情节、思想主旨
3. 简单难度：个人朗诵或简短演讲，准备时间短；中等：小组情景剧，有排练环节；困难：完整话剧或大型演出，有剧本创作
4. 提供具体的表演要点：台词方向、情感表达
5. 提交要求包括演出视频（简单：手机录制即可；困难：需要正式录制）

{common_rules}

请以JSON格式输出：
{json_format}"""

        elif practice_type == PracticeType.WRITING:
            return f"""你是一位经验丰富的高校思政课实践教学设计专家。

请为大学生设计一个【写作设计类】实践方案。

{base_context}

{difficulty_rules}

具体要求：
1. 明确写作体裁（选最适合该知识点的）：
   - 简单：读书笔记、心得体会（500-800字）
   - 中等：调研报告、新闻评论（1500-2000字，需引用文献）
   - 困难：学术论文、深度案例分析（3000字以上，规范格式，多方论证）
2. 提供详细写作框架：引言结构、正文论证思路、论据来源建议
3. 步骤包含：确定选题→资料检索→（中等/困难：实地调研/访谈）→撰写大纲→完成初稿→修改定稿

{common_rules}

请以JSON格式输出：
{json_format}"""

        elif practice_type == PracticeType.PRESENTATION:
            return f"""你是一位经验丰富的高校思政课实践教学设计专家。

请为大学生设计一个【宣传表达类】实践方案。

{base_context}

{difficulty_rules}

具体要求：
1. 设计具体宣传形式：
   - 简单：制作1张海报或写1篇推文
   - 中等：短视频制作（1-3分钟）或系列海报
   - 困难：完整宣传策划（多平台传播，含数据分析）
2. 提供内容框架：核心观点、素材来源、视觉/文案方向
3. 要求作品兼具思想性和创意性
4. 提交要求：策划文档、成品（图片/视频）、（困难：传播数据截图）

{common_rules}

请以JSON格式输出：
{json_format}"""

        elif practice_type == PracticeType.INTERACTION:
            return f"""你是一位经验丰富的高校思政课实践教学设计专家。

请为大学生设计一个【交往行动类】实践方案。

{base_context}

{difficulty_rules}

具体要求：
1. 设计具体互动形式：
   - 简单：访谈1-2人，完成简短记录
   - 中等：社区志愿服务或小规模问卷调查（20份以上）
   - 困难：系统性社会调研（50份以上问卷+深度访谈+数据分析报告）
2. 明确互动对象和方式：与谁互动、在哪互动、互动什么
3. 提供具体互动指引：访谈提纲模板、问卷设计方向

{common_rules}

请以JSON格式输出：
{json_format}"""

        elif practice_type == PracticeType.PRODUCTION:
            return f"""你是一位经验丰富的高校思政课实践教学设计专家。

请为大学生设计一个【生产改造类】实践方案。

{base_context}

{difficulty_rules}

具体要求：
1. 设计具体创作形式：
   - 简单：手工制作、简单绘画或基础设计稿
   - 中等：文创产品设计、多媒体作品（需要一定技术）
   - 困难：完整创新项目（小程序/装置艺术/系统性设计方案，需要多种技能整合）
2. 提供设计思路：创意来源与知识点关联、设计理念、实现路径
3. 每个步骤说明具体操作方法
4. 提交要求：设计草图、制作过程照片/视频、成品展示、设计说明

{common_rules}

请以JSON格式输出：
{json_format}"""

        return ""

    def _parse_response(self, response: str, practice_type: PracticeType) -> Dict[str, Any]:
        """解析LLM响应，清理推理标签和markdown包裹"""
        import re

        cleaned = response.strip()

        # 1. 去除 <think>...</think> 推理标签（DeepSeek等模型）
        cleaned = re.sub(r'<think>[\s\S]*?</think>', '', cleaned).strip()

        # 2. 去除 markdown 代码块包裹
        if '```json' in cleaned:
            cleaned = cleaned.split('```json')[1].split('```')[0].strip()
        elif '```' in cleaned:
            cleaned = cleaned.split('```')[1].split('```')[0].strip()

        # 3. 尝试提取第一个 JSON 对象（跳过前导文本）
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            cleaned = json_match.group()

        try:
            plan_data = json.loads(cleaned)
            if "title" not in plan_data:
                plan_data["title"] = f"{practice_type.value}实践方案"
            if "content" not in plan_data:
                plan_data["content"] = "实践方案内容"
            if "tasks" not in plan_data:
                plan_data["tasks"] = []
            if "estimated_hours" not in plan_data:
                plan_data["estimated_hours"] = 3
            if "difficulty" not in plan_data:
                plan_data["difficulty"] = "easy"
            return plan_data
        except json.JSONDecodeError:
            return {
                "title": f"{practice_type.value}实践方案",
                "content": cleaned,
                "tasks": [
                    {"task": "完成实践活动", "description": "按照方案要求完成实践", "required": True}
                ],
                "venues": [],
                "estimated_hours": 3,
                "difficulty": "easy"
            }
