# -*- coding: utf-8 -*-

"""
AI Daily Report Generator
基于AI标签消息生成每日报告
"""

import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
from collections import defaultdict
import uuid

from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.database.connection import create_session
from backend.database.entities import AIDailyReport
from backend.database.orm_registry import get_orm_registry

logger = logging.getLogger(__name__)


class AIReportGenerator:
    """
    AI日报生成器

    功能：
    - 查询过去24小时的AI标签消息
    - 聚合统计数据（数量、地区分布、消息源等）
    - 调用LLM生成结构化日报
    - 保存到数据库
    """

    def __init__(self):
        """初始化日报生成器"""
        self._llm_client = None
        self.registry = get_orm_registry()

    def _get_llm_client(self):
        """延迟加载Fast LLM客户端"""
        if self._llm_client is None:
            from backend.llm import get_fast_client
            self._llm_client = get_fast_client()

            if self._llm_client is None:
                logger.error("【AIReportGenerator】Fast LLM客户端未初始化")
                raise RuntimeError("Fast LLM client not initialized")

        return self._llm_client

    def _collect_messages_from_last_24h(self, db: Session) -> Dict[str, List[Dict]]:
        """
        收集过去24小时的AI标签消息

        Args:
            db: 数据库会话

        Returns:
            按ai_tag分类的消息字典
        """
        cutoff_time = datetime.now() - timedelta(hours=24)

        messages_by_tag = defaultdict(list)
        ai_tag_models = self.registry.get_ai_tag_models()

        logger.info(f"【AIReportGenerator】开始收集消息（截止时间：{cutoff_time}）")
        logger.info(f"【AIReportGenerator】扫描{len(ai_tag_models)}个表：{self.registry.get_ai_tag_table_names()}")

        total_collected = 0

        for model_class in ai_tag_models:
            table_name = model_class.__tablename__

            try:
                # 查询过去24小时且有ai_tag的消息
                query = db.query(model_class).filter(
                    and_(
                        model_class.ai_tag.isnot(None),
                        model_class.ai_tag != '',
                        model_class.crawled_at >= cutoff_time
                    )
                ).order_by(model_class.crawled_at.desc())

                records = query.all()

                for record in records:
                    ai_tag = record.ai_tag

                    # 安全获取字段
                    message_data = {
                        'id': str(record.id),
                        'title': getattr(record, 'title', ''),
                        'summary': getattr(record, 'summary', '') or getattr(record, 'content', '')[:200],
                        'content': getattr(record, 'content', ''),
                        'source_name': getattr(record, 'source_name', 'unknown'),
                        'region': getattr(record, 'region', None),
                        'industry_tags': getattr(record, 'industry_tags', None),
                        'published_at': getattr(record, 'published_at', None),
                        'crawled_at': record.crawled_at,
                        'url': getattr(record, 'url', None),
                        'table_name': table_name
                    }

                    messages_by_tag[ai_tag].append(message_data)
                    total_collected += 1

                logger.info(f"【AIReportGenerator】{table_name}: 收集到{len(records)}条消息")

            except Exception as e:
                logger.error(f"【AIReportGenerator】从{table_name}收集消息失败: {e}", exc_info=True)
                continue

        logger.info(f"【AIReportGenerator】共收集{total_collected}条消息")
        logger.info(f"  - AI治理信息: {len(messages_by_tag.get('AI治理信息', []))}条")
        logger.info(f"  - AI科研信息: {len(messages_by_tag.get('AI科研信息', []))}条")
        logger.info(f"  - AI产业信息: {len(messages_by_tag.get('AI产业信息', []))}条")

        return dict(messages_by_tag)

    def _aggregate_statistics(self, messages_by_tag: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        聚合统计数据

        Args:
            messages_by_tag: 按标签分类的消息

        Returns:
            统计数据字典
        """
        stats = {
            'governance_count': len(messages_by_tag.get('AI治理信息', [])),
            'research_count': len(messages_by_tag.get('AI科研信息', [])),
            'industry_count': len(messages_by_tag.get('AI产业信息', [])),
            'total_messages': 0,
            'region_distribution': {},
            'source_distribution': {},
            'industry_distribution': {}
        }

        stats['total_messages'] = stats['governance_count'] + stats['research_count'] + stats['industry_count']

        # 统计地区分布
        region_counts = defaultdict(int)
        source_counts = defaultdict(int)
        industry_counts = defaultdict(int)

        for tag, messages in messages_by_tag.items():
            for msg in messages:
                # 地区统计
                if msg.get('region'):
                    region = msg['region'].split('/')[0]  # 取顶级地区（如"中国/广东省"→"中国"）
                    region_counts[region] += 1

                # 消息源统计
                source_counts[msg.get('source_name', 'unknown')] += 1

                # 行业标签统计
                if msg.get('industry_tags'):
                    tags = msg['industry_tags'].split(',')
                    for tag in tags:
                        industry_counts[tag.strip()] += 1

        stats['region_distribution'] = dict(sorted(region_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        stats['source_distribution'] = dict(sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        stats['industry_distribution'] = dict(sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)[:10])

        return stats

    def _build_report_prompt(
        self,
        messages_by_tag: Dict[str, List[Dict]],
        stats: Dict[str, Any],
        report_date: date
    ) -> List[Dict[str, str]]:
        """
        构建日报生成提示词

        Args:
            messages_by_tag: 按标签分类的消息
            stats: 统计数据
            report_date: 报告日期

        Returns:
            消息列表（system/user格式）
        """
        # System消息：定义角色和报告规范
        system_content = """你是一位专业的AI行业分析师，擅长撰写结构化的AI日报。

报告要求：
1. 使用Markdown格式
2. 结构清晰：标题、摘要、三大板块、重点事件、趋势分析
3. 语言专业且易读，分析深入透彻
4. 突出关键信息和数据洞察
5. 深度分析每个重点事件，不仅列举事实，更要挖掘背后的含义、影响和趋势
6. 结合不同事件之间的关联性进行综合分析
7. 提供有见地的观点和前瞻性判断
8. 不限制事件数量，确保覆盖所有重要信息
9. 字数不限，以深度和完整性为优先"""

        # 格式化日期
        date_str = report_date.strftime('%Y年%m月%d日')

        # User消息：提供数据和要求
        user_content = f"""今天是{date_str}，请根据以下数据生成今日AI日报：

## 统计概览
- 总消息数：{stats['total_messages']}条
- AI治理信息：{stats['governance_count']}条
- AI科研信息：{stats['research_count']}条
- AI产业信息：{stats['industry_count']}条

## 地区分布（Top 10）
{self._format_distribution(stats['region_distribution'])}

## 消息来源（Top 10）
{self._format_distribution(stats['source_distribution'])}

## 行业标签（Top 10）
{self._format_distribution(stats['industry_distribution'])}

## AI治理信息详情（全部{stats['governance_count']}条）
{self._format_messages(messages_by_tag.get('AI治理信息', []))}

## AI科研信息详情（全部{stats['research_count']}条）
{self._format_messages(messages_by_tag.get('AI科研信息', []))}

## AI产业信息详情（全部{stats['industry_count']}条）
{self._format_messages(messages_by_tag.get('AI产业信息', []))}

---

请生成结构化的日报，包含以下部分：

1. **标题**：包含日期，体现当日核心主题

2. **摘要**：用3-5段话深入概括今日要点，不仅列举事件，更要指出其意义和影响

3. **AI治理板块**：
   - 覆盖所有重要事件，不限数量
   - 对每个事件进行深度分析：背景、影响、政策导向、国际对比
   - 挖掘事件之间的关联性和趋势
   - 提供你的专业见解和判断

4. **AI科研板块**：
   - 覆盖所有重要事件，不限数量
   - 深入解读技术突破、研究方向、创新意义
   - 分析学术成果对产业的潜在影响
   - 识别研究热点和前沿趋势

5. **AI产业板块**：
   - 覆盖所有重要事件，不限数量
   - 深度剖析商业动态、市场变化、竞争格局
   - 分析企业战略、投资趋势、产业链变化
   - 评估产业发展的机遇与挑战

6. **综合趋势分析**：
   - 跨板块综合分析：治理-科研-产业的互动关系
   - 识别宏观趋势：技术发展方向、政策演变路径、市场变化规律
   - 前瞻性判断：未来可能的发展方向和关键变化
   - 战略性建议：值得关注的领域和需要警惕的风险

**分析深度要求**：
- 不要浅尝辄止，要深入挖掘事件背后的逻辑
- 不要简单罗列，要建立事件之间的联系
- 不要仅陈述事实，要提供洞察和判断
- 结合历史背景和国际视野进行分析
- 体现专业分析师的独特价值"""

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]

    def _format_distribution(self, distribution: Dict[str, int]) -> str:
        """格式化分布数据"""
        if not distribution:
            return "（无数据）"

        lines = []
        for key, count in distribution.items():
            lines.append(f"- {key}: {count}条")
        return "\n".join(lines)

    def _format_messages(self, messages: List[Dict]) -> str:
        """格式化消息列表"""
        if not messages:
            return "（无数据）"

        lines = []
        for i, msg in enumerate(messages, 1):
            published_at = msg.get('published_at')
            time_str = published_at.strftime('%m-%d %H:%M') if published_at else '未知时间'

            line = f"{i}. [{msg['source_name']}] {msg['title']}"
            if msg.get('region'):
                line += f" | 地区：{msg['region']}"
            line += f" | {time_str}"
            lines.append(line)

        return "\n".join(lines)

    async def _generate_report_content(
        self,
        messages_by_tag: Dict[str, List[Dict]],
        stats: Dict[str, Any],
        report_date: date
    ) -> str:
        """
        调用LLM生成报告内容

        Args:
            messages_by_tag: 按标签分类的消息
            stats: 统计数据
            report_date: 报告日期

        Returns:
            生成的报告内容（Markdown格式）
        """
        llm_client = self._get_llm_client()
        messages = self._build_report_prompt(messages_by_tag, stats, report_date)

        try:
            logger.info("【AIReportGenerator】调用LLM生成报告...")

            # 异步调用LLM
            response = await llm_client.generate_with_messages_async(messages)

            # 提取生成的内容
            if hasattr(response, 'choices') and len(response.choices) > 0:
                content = response.choices[0].message.content
                logger.info(f"【AIReportGenerator】报告生成成功（长度：{len(content)}字符）")
                return content
            else:
                raise ValueError("LLM返回格式异常")

        except Exception as e:
            logger.error(f"【AIReportGenerator】LLM生成失败: {e}", exc_info=True)
            # 降级策略：返回简单的统计摘要
            return self._generate_fallback_report(stats)

    def _generate_fallback_report(self, stats: Dict[str, Any]) -> str:
        """
        生成降级报告（LLM失败时）

        Args:
            stats: 统计数据

        Returns:
            简单的统计摘要
        """
        today = datetime.now().strftime('%Y年%m月%d日')

        report = f"""# AI日报 - {today}

[AI生成暂不可用，以下为统计摘要]

## 数据概览

- **总消息数**: {stats['total_messages']}条
- **AI治理信息**: {stats['governance_count']}条
- **AI科研信息**: {stats['research_count']}条
- **AI产业信息**: {stats['industry_count']}条

## 地区分布

{self._format_distribution(stats['region_distribution'])}

## 消息来源

{self._format_distribution(stats['source_distribution'])}

## 行业标签

{self._format_distribution(stats['industry_distribution'])}

---

*注意：由于AI服务暂不可用，本报告仅包含统计数据。完整分析报告将在服务恢复后重新生成。*
"""
        return report

    async def generate_daily_report(self, report_date: Optional[datetime] = None) -> Optional[str]:
        """
        生成每日报告

        Args:
            report_date: 报告日期（默认为今天）

        Returns:
            报告ID（UUID），失败返回None
        """
        if report_date is None:
            report_date = datetime.now().date()

        logger.info(f"【AIReportGenerator】开始生成{report_date}的AI日报")

        try:
            with create_session() as db:
                # 检查是否已存在报告
                existing_report = db.query(AIDailyReport).filter(
                    AIDailyReport.report_date == report_date
                ).first()

                if existing_report:
                    logger.warning(f"【AIReportGenerator】{report_date}的报告已存在（ID: {existing_report.id}）")
                    return existing_report.id

                # 收集消息
                messages_by_tag = self._collect_messages_from_last_24h(db)

                # 聚合统计
                stats = self._aggregate_statistics(messages_by_tag)

                # 检查是否有数据
                if stats['total_messages'] == 0:
                    logger.warning("【AIReportGenerator】无AI标签消息，跳过报告生成")
                    return None

                # 生成报告内容（异步调用LLM）
                report_content = await self._generate_report_content(messages_by_tag, stats, report_date)

                # 保存到数据库
                report_id = str(uuid.uuid4())
                report = AIDailyReport(
                    id=report_id,
                    report_date=report_date,
                    content=report_content,
                    statistics=stats,
                    governance_count=stats['governance_count'],
                    research_count=stats['research_count'],
                    industry_count=stats['industry_count'],
                    total_messages=stats['total_messages'],
                    generation_status='completed',
                    error_message=None,
                    generated_at=datetime.now(),
                    model_version=self._get_llm_client().model
                )

                db.add(report)
                db.commit()

                logger.info(f"【AIReportGenerator】报告生成成功（ID: {report_id}）")
                return report_id

        except Exception as e:
            logger.error(f"【AIReportGenerator】生成报告失败: {e}", exc_info=True)

            # 记录失败状态
            try:
                with create_session() as db:
                    failed_report = AIDailyReport(
                        id=str(uuid.uuid4()),
                        report_date=report_date,
                        content="",
                        statistics={},
                        governance_count=0,
                        research_count=0,
                        industry_count=0,
                        total_messages=0,
                        generation_status='failed',
                        error_message=str(e)[:500],
                        generated_at=datetime.now(),
                        model_version='N/A'
                    )
                    db.add(failed_report)
                    db.commit()
            except Exception as save_error:
                logger.error(f"【AIReportGenerator】保存失败记录异常: {save_error}")

            return None


# 全局单例
_report_generator = None


def get_report_generator() -> AIReportGenerator:
    """获取全局日报生成器实例"""
    global _report_generator
    if _report_generator is None:
        _report_generator = AIReportGenerator()
    return _report_generator
