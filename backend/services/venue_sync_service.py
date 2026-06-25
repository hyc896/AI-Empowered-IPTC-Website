# -*- coding: utf-8 -*-

"""
场馆同步服务
从 iptc_main.iptc_cases 中提取上海地区案例的实践场馆，写入 iptc_practice.venues
"""

import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

_EXTRACT_SYSTEM_PROMPT = """你是一个专业的实践场馆信息提取助手。
你的任务是从思政课案例内容中识别并提取适合学生开展实践活动的具体场馆或地点。

提取规则：
1. 只提取真实存在、学生可实地前往的具体场馆、纪念馆、博物馆、基地、社区等地点
2. 每个场馆必须有明确的地名（如"上海市XXX纪念馆"），不接受模糊描述
3. 必须说明该场馆与案例思政内容的关联理由（1-2句话）
4. 不提取虚构场所、抽象概念或泛泛的区域名称

返回格式（严格JSON数组）：
[
  {
    "name": "场馆全称",
    "address": "详细地址（尽量精确到街道或门牌）",
    "relevance_reason": "与该案例思政内容的关联理由"
  }
]

如果案例中没有明确提及可供实践的具体场馆，返回空数组：[]"""


def _get_db_config() -> dict:
    """从一期 config.yaml 读取 MySQL 连接参数"""
    import os
    from backend.config.config_manager import ConfigManager

    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'config.yaml'
    )
    cm = ConfigManager()
    cm.load_config(config_path)
    return cm.get_config().get('database', {}).get('mysql', {})


def _build_engine(db_config: dict, database: str):
    """构造指定 database 的 SQLAlchemy 引擎"""
    url = (
        f"mysql+pymysql://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{database}"
        f"?charset={db_config.get('charset', 'utf8mb4')}"
    )
    return create_engine(
        url,
        pool_size=5,
        max_overflow=5,
        pool_recycle=3600,
        pool_pre_ping=True,
    )


class VenueSyncService:
    """
    场馆同步服务

    读取 iptc_main.iptc_cases（primary_region='上海'，mentioned_locations IS NULL）
    → LLM 提取场馆 → 写入 iptc_practice.venues，同时回写 mentioned_locations
    """

    def __init__(self):
        db_config = _get_db_config()
        self._main_engine = _build_engine(db_config, 'iptc_main')
        self._practice_engine = _build_engine(db_config, 'iptc_practice')
        self._main_session = sessionmaker(bind=self._main_engine, autocommit=False, autoflush=False)
        self._practice_session = sessionmaker(bind=self._practice_engine, autocommit=False, autoflush=False)

    async def sync_venues_from_cases(self) -> dict:
        """
        主入口：扫描上海案例并提取场馆

        Returns:
            {'synced': int, 'skipped': int, 'venues_added': int}
        """
        from backend.llm.global_llm_manager import get_fast_client

        client = get_fast_client()
        if client is None:
            raise RuntimeError("Fast LLM 客户端未初始化")

        cases = self._fetch_pending_cases()
        logger.info(f"【场馆同步】找到 {len(cases)} 条待处理上海案例")

        synced = 0
        skipped = 0
        venues_added = 0

        for case in cases:
            case_id = case['id']
            try:
                venues = await self._extract_venues(client, case)
                self._write_venues(case_id, venues)
                self._mark_case_processed(case_id, venues)
                venues_added += len(venues)
                synced += 1
                logger.info(f"【场馆同步】案例 {case_id[:8]}... 提取到 {len(venues)} 个场馆")
            except Exception as e:
                logger.error(f"【场馆同步】案例 {case_id[:8]}... 处理失败: {e}", exc_info=True)
                skipped += 1

        logger.info(f"【场馆同步】完成 — 已处理 {synced}，跳过 {skipped}，新增场馆 {venues_added}")
        return {'synced': synced, 'skipped': skipped, 'venues_added': venues_added}

    def _fetch_pending_cases(self) -> List[dict]:
        """查询待处理的上海案例（mentioned_locations IS NULL）"""
        sql = text("""
            SELECT id, title, content
            FROM iptc_cases
            WHERE primary_region = '上海'
              AND mentioned_locations IS NULL
            ORDER BY created_at DESC
            LIMIT 200
        """)
        with self._main_engine.connect() as conn:
            rows = conn.execute(sql).fetchall()
        return [{'id': str(r[0]), 'title': r[1], 'content': r[2]} for r in rows]

    async def _extract_venues(self, client, case: dict) -> List[dict]:
        """
        调用 LLM 从案例文本中提取场馆列表

        Returns:
            [{'name': str, 'address': str, 'relevance_reason': str}]
        """
        content_preview = (case['content'] or '')[:3000]
        user_msg = f"案例标题：{case['title']}\n\n案例内容：\n{content_preview}"

        messages = [
            {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        response = await client.generate_with_messages_async(
            messages,
            source="venue_sync",
            temperature=0.2,
            max_tokens=1500,
        )

        raw = response.choices[0].message.content.strip()
        return self._parse_venues(raw)

    def _parse_venues(self, raw: str) -> List[dict]:
        """解析 LLM 返回的 JSON 场馆列表"""
        try:
            # 提取 JSON 数组（防止 LLM 在前后添加说明文字）
            start = raw.find('[')
            end = raw.rfind(']') + 1
            if start == -1 or end == 0:
                return []
            data = json.loads(raw[start:end])
            result = []
            for item in data:
                name = (item.get('name') or '').strip()
                if not name:
                    continue
                result.append({
                    'name': name,
                    'address': (item.get('address') or '').strip(),
                    'relevance_reason': (item.get('relevance_reason') or '').strip(),
                })
            return result
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"【场馆同步】JSON 解析失败: {e}，原始内容: {raw[:200]}")
            return []

    def _write_venues(self, case_id: str, venues: List[dict]) -> None:
        """将提取的场馆写入 iptc_practice.venues（跳过同名已存在记录）"""
        if not venues:
            return

        now = datetime.now()
        insert_sql = text("""
            INSERT IGNORE INTO venues
                (id, name, address, source, case_id, relevance_reason,
                 is_verified, is_active, created_at, updated_at)
            VALUES
                (:id, :name, :address, :source, :case_id, :relevance_reason,
                 0, 1, :created_at, :updated_at)
        """)

        with self._practice_engine.begin() as conn:
            for v in venues:
                conn.execute(insert_sql, {
                    'id': str(uuid.uuid4()),
                    'name': v['name'],
                    'address': v['address'],
                    'source': 'ai_extract',
                    'case_id': case_id,
                    'relevance_reason': v['relevance_reason'],
                    'created_at': now,
                    'updated_at': now,
                })

    def _mark_case_processed(self, case_id: str, venues: List[dict]) -> None:
        """回写 iptc_cases.mentioned_locations，标记该案例已处理"""
        location_names = [v['name'] for v in venues] if venues else []
        update_sql = text("""
            UPDATE iptc_cases
            SET mentioned_locations = :locations, updated_at = :now
            WHERE id = :case_id
        """)
        with self._main_engine.begin() as conn:
            conn.execute(update_sql, {
                'locations': json.dumps(location_names, ensure_ascii=False),
                'case_id': case_id,
                'now': datetime.now(),
            })
