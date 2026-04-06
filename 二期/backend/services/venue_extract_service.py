# -*- coding: utf-8 -*-

"""
场馆信息提取服务
从上海消息中提取场馆信息，存入 venues 表
"""

import uuid
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database.entities import Venue

project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / "config" / ".env")

logger = logging.getLogger(__name__)

# 上海场馆关键词，用于快速过滤
VENUE_KEYWORDS = [
    '博物馆', '纪念馆', '展览馆', '美术馆', '科技馆', '文化馆', '图书馆',
    '红色基地', '爱国主义教育基地', '党史教育基地', '革命遗址', '烈士陵园',
    '纪念地', '故居', '旧址', '遗址', '纪念碑', '纪念堂',
    '文化中心', '社区中心', '活动中心', '青少年中心',
    '公园', '广场', '景区', '景点',
]


class VenueExtractService:
    """场馆信息提取服务"""

    def __init__(self, db: Session):
        self.db = db
        self._llm_client = None

    def _get_llm_client(self):
        if self._llm_client is None:
            import requests
            api_key = os.getenv("LLM_API_KEY", "")
            base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
            model = os.getenv("LLM_MODEL", "deepseek-chat")

            class _Client:
                def chat(self, prompt: str) -> str:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "你是场馆信息提取专家，请严格按照JSON格式输出，不要输出任何其他内容。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1000
                    }
                    resp = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=30)
                    resp.raise_for_status()
                    content = resp.json()["choices"][0]["message"]["content"]
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()
                    return content

            self._llm_client = _Client()
        return self._llm_client

    def _contains_venue_keyword(self, text: str) -> bool:
        return any(kw in text for kw in VENUE_KEYWORDS)

    def extract_from_message(self, title: str, content: str, source_url: str) -> List[Dict[str, Any]]:
        """
        从单条消息中提取场馆信息

        Args:
            title: 文章标题
            content: 文章正文
            source_url: 来源URL

        Returns:
            提取到的场馆信息列表
        """
        text = f"{title} {content}"
        if not self._contains_venue_keyword(text):
            return []

        prompt = f"""从以下上海新闻文章中提取场馆信息。只提取上海地区的实体场馆（博物馆、纪念馆、红色基地、文化中心等），不要提取虚构或不确定的场所。

文章标题：{title}
文章内容：{content[:800]}

请以JSON数组格式输出，每个场馆包含以下字段：
- name: 场馆名称（必填）
- category: 类别（博物馆/纪念馆/红色基地/文化中心/公园/其他）
- address: 地址（如文章中有提及）
- description: 简介（从文章中提取，不超过100字）

如果文章中没有明确的场馆信息，返回空数组 []。

输出格式示例：
[{{"name": "上海博物馆", "category": "博物馆", "address": "上海市黄浦区人民大道201号", "description": "..."}}]"""

        try:
            client = self._get_llm_client()
            response = client.chat(prompt)
            venues = json.loads(response)
            if not isinstance(venues, list):
                return []
            return venues
        except Exception as e:
            logger.error(f"场馆提取LLM调用失败: {e}")
            return []

    def save_venues(self, venue_list: List[Dict[str, Any]], source_url: str) -> int:
        """
        将提取到的场馆信息存入数据库（去重）

        Args:
            venue_list: 场馆信息列表
            source_url: 来源URL

        Returns:
            新增场馆数量
        """
        saved = 0
        for v in venue_list:
            name = v.get('name', '').strip()
            if not name:
                continue
            # 按名称去重
            existing = self.db.query(Venue).filter(Venue.name == name).first()
            if existing:
                logger.debug(f"场馆已存在，跳过: {name}")
                continue

            address = v.get('address', '上海')
            if not address:
                address = '上海'

            venue = Venue(
                id=str(uuid.uuid4()),
                name=name,
                category=v.get('category', '其他'),
                address=address,
                description=v.get('description'),
                source='上海消息源',
                source_url=source_url,
                is_verified=False,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            try:
                self.db.add(venue)
                self.db.commit()
                saved += 1
                logger.info(f"新增场馆: {name}")
            except Exception as e:
                self.db.rollback()
                logger.error(f"场馆存储失败 {name}: {e}")

        return saved

    def process_shanghai_messages(self, limit: int = 50) -> Dict[str, int]:
        """
        批量处理上海消息，提取场馆信息

        Args:
            limit: 每次处理的最大消息数

        Returns:
            处理统计 {processed, extracted, saved}
        """
        from database.entities import ShanghaiObserverMessage, ThepaperShanghaiMessage, EastdayMessage
        from sqlalchemy import text

        stats = {'processed': 0, 'extracted': 0, 'saved': 0}

        # 从一期数据库读取上海消息（通过跨库查询或直接连接一期DB）
        # 这里通过一期API接口获取，避免直接操作一期数据库
        try:
            import requests
            api_base = os.getenv("CASE_API_BASE_URL", "http://localhost:11528")
            resp = requests.get(
                f"{api_base}/api/v1/sources/messages",
                params={"category": "上海", "limit": limit},
                timeout=10
            )
            if not resp.ok:
                logger.warning(f"获取上海消息失败: {resp.status_code}")
                return stats

            messages = resp.json().get('items', resp.json() if isinstance(resp.json(), list) else [])
            logger.info(f"获取到 {len(messages)} 条上海消息")

            for msg in messages:
                stats['processed'] += 1
                title = msg.get('title', '')
                content = msg.get('content', msg.get('summary', ''))
                url = msg.get('url', '')

                venues = self.extract_from_message(title, content, url)
                if venues:
                    stats['extracted'] += len(venues)
                    stats['saved'] += self.save_venues(venues, url)

        except Exception as e:
            logger.error(f"批量处理上海消息失败: {e}")

        return stats
