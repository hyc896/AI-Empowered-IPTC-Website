# -*- coding: utf-8 -*-

"""
AI Daily Report Generator
基于AI标签消息生成每日报告
"""

import asyncio
import logging
from datetime import datetime, timedelta, date, time
from typing import Dict, List, Any, Optional
from collections import defaultdict
import uuid

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

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

    输入控制：
    - 最大输入tokens: 88000（约44000中文字）
    - 最大输出tokens: 16000（约8000中文字）
    - 总上下文窗口: 128000 tokens
    """

    # 输入token限制（确保输出有足够空间）
    MAX_INPUT_TOKENS = 88000
    MAX_OUTPUT_TOKENS = 16000

    def __init__(self):
        """初始化日报生成器"""
        self._llm_client = None

        # 确保ORM类已注册（Celery solo pool模式下worker_process_init不会触发）
        from backend.database.orm_registry import auto_register_all_models
        auto_register_all_models()

        self.registry = get_orm_registry()

    def _get_llm_client(self):
        """延迟加载Chat LLM客户端（AI日报生成需要更强的推理能力和更长的超时时间）"""
        if self._llm_client is None:
            from backend.llm import get_chat_client
            self._llm_client = get_chat_client()

            if self._llm_client is None:
                logger.error("【AIReportGenerator】Chat LLM客户端未初始化")
                raise RuntimeError("Chat LLM client not initialized")

        return self._llm_client

    def _collect_messages_from_last_24h(
        self,
        db: Session,
        report_date: date,
        ai_tag_filter: Optional[str] = None
    ) -> Dict[str, List[Dict]]:
        """
        收集指定日期过去24小时的AI标签消息

        Args:
            db: 数据库会话
            report_date: 报告日期
            ai_tag_filter: 可选的ai_tag过滤器，只收集特定分类的消息
                          - None: 收集所有分类（用于综合日报）
                          - 'AI治理信息': 只收集治理类消息
                          - 'AI科研信息': 只收集科研类消息
                          - 'AI产业信息': 只收集产业类消息

        Returns:
            按ai_tag分类的消息字典
        """
        # 计算时间范围
        today = datetime.now().date()
        if report_date >= today:
            # 如果是今天或未来日期，从现在往前推24小时
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
        else:
            # 如果是历史日期，从当天23:59:59往前推24小时
            end_time = datetime.combine(report_date, time(23, 59, 59))
            start_time = end_time - timedelta(hours=24)

        messages_by_tag = defaultdict(list)
        ai_tag_models = self.registry.get_ai_tag_models()

        filter_msg = f"（过滤：{ai_tag_filter}）" if ai_tag_filter else "（收集全部）"
        logger.info(f"【AIReportGenerator】开始收集消息{filter_msg}（时间范围：{start_time} ~ {end_time}）")
        logger.info(f"【AIReportGenerator】扫描{len(ai_tag_models)}个表：{self.registry.get_ai_tag_table_names()}")

        total_collected = 0

        for model_class in ai_tag_models:
            table_name = model_class.__tablename__

            try:
                # 构建查询条件
                conditions = [
                    model_class.ai_tag.isnot(None),
                    model_class.ai_tag != '',
                    model_class.crawled_at >= start_time,
                    model_class.crawled_at <= end_time
                ]

                # 如果指定了ai_tag_filter，添加过滤条件
                if ai_tag_filter:
                    conditions.append(model_class.ai_tag == ai_tag_filter)

                # 查询过去24小时且符合条件的消息（预加载source关系避免N+1查询）
                query = db.query(model_class).options(joinedload(model_class.source)).filter(and_(*conditions)).order_by(model_class.crawled_at.desc())

                records = query.all()

                for record in records:
                    ai_tag = record.ai_tag

                    # 安全获取字段
                    message_data = {
                        'id': str(record.id),
                        'title': getattr(record, 'title', ''),
                        'summary': getattr(record, 'summary', '') or getattr(record, 'content', '')[:200],
                        'content': getattr(record, 'content', ''),
                        'source_name': (record.source.display_name or record.source.name) if record.source else 'unknown',
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
    ) -> tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
        """
        构建日报生成提示词（带引用系统）

        Args:
            messages_by_tag: 按标签分类的消息
            stats: 统计数据
            report_date: 报告日期

        Returns:
            (messages, reference_list)
            - messages: 消息列表（system/user格式）
            - reference_list: 引用列表（用于后处理添加参考来源）
        """
        # 1. 收集所有消息并构建引用映射（每条消息独立编号）
        all_messages = []
        for tag, msgs in messages_by_tag.items():
            all_messages.extend(msgs)

        message_index, reference_list = self._build_message_references(all_messages)

        logger.info(f"【AIReportGenerator】构建了{len(reference_list)}条消息引用")

        # System消息：定义角色和报告规范（使用序号引用格式）
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
9. 字数不限，以深度和完整性为优先

内容撰写与消息源引用规范（必须严格遵守）：
1. 切记不要过度压缩：针对每条新闻不要只用一句话概括，要铺开阐释，深入展开背景、细节、影响等
2. 每个事件后必须用方括号标注引用序号，如：[1]、[2]、[1][3]（多个来源）
3. 引用序号对应输入数据中的"引用X"标记，请务必准确匹配
4. 如果同一事件来自多个消息源，连续标注多个序号：[1][2][5]
5. 引用格式示例："OpenAI宣布了新的GPT-5模型[1][3]。该模型在推理能力上有显著提升，特别是在数学和代码生成方面。"
6. 不要在方括号中写消息源名称，只写序号
7. 参考来源列表会由系统自动添加，你不需要在报告中生成
8. 引用尾注不要过于频繁：同一个引用序号在同一个大段落内最多只出现一次，避免重复标注同一来源

内容优先级原则：
1. 最新发布的AI模型是时效性最高的内容，应作为最重要的事件优先报道和深度分析
2. 模型发布相关新闻（如GPT、Claude、Gemini等新版本）应放在显著位置，详细分析其技术突破和行业影响

客观性与中立性原则：
1. 对涉及中国的负面信息，必须保持中性和怀疑的态度
2. 对明显带有偏见或攻击性的描述，进行中性过滤和客观改写
3. 多角度呈现信息，避免单一立场的片面描述
4. 区分事实陈述和观点评论，对争议性内容提供平衡视角"""

        # 格式化日期
        date_str = report_date.strftime('%Y年%m月%d日')

        # 计算固定部分的token数
        system_tokens = self._estimate_tokens(system_content)

        # 构建统计部分
        stats_section = f"""## 统计概览
- 总消息数：{stats['total_messages']}条
- AI治理信息：{stats['governance_count']}条
- AI科研信息：{stats['research_count']}条
- AI产业信息：{stats['industry_count']}条

## 地区分布（Top 10）
{self._format_distribution(stats['region_distribution'])}

## 消息来源（Top 10）
{self._format_distribution(stats['source_distribution'])}

## 行业标签（Top 10）
{self._format_distribution(stats['industry_distribution'])}"""

        stats_tokens = self._estimate_tokens(stats_section)

        # 要求部分
        requirements = """---

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

        requirements_tokens = self._estimate_tokens(requirements)

        # 计算消息详情可用的token数
        # 总限制 - system - 统计 - 要求 - 开头文本（今天是...）
        header_text = f"今天是{date_str}，请根据以下数据生成今日AI日报："
        header_tokens = self._estimate_tokens(header_text)

        available_tokens = self.MAX_INPUT_TOKENS - system_tokens - stats_tokens - requirements_tokens - header_tokens
        # 三个板块平均分配（每个约25000 tokens）
        tokens_per_section = available_tokens // 3

        logger.info(
            f"【AIReportGenerator】Token分配 - "
            f"总限制:{self.MAX_INPUT_TOKENS}, "
            f"system:{system_tokens}, "
            f"stats:{stats_tokens}, "
            f"requirements:{requirements_tokens}, "
            f"可用:{available_tokens}, "
            f"每板块:{tokens_per_section}"
        )

        # 格式化消息详情（带token限制和引用序号）
        governance_text, governance_ids = self._format_messages(messages_by_tag.get('AI治理信息', []), max_tokens=tokens_per_section, message_index=message_index)
        research_text, research_ids = self._format_messages(messages_by_tag.get('AI科研信息', []), max_tokens=tokens_per_section, message_index=message_index)
        industry_text, industry_ids = self._format_messages(messages_by_tag.get('AI产业信息', []), max_tokens=tokens_per_section, message_index=message_index)

        governance_section = f"\n## AI治理信息详情（全部{stats['governance_count']}条）\n{governance_text}"
        research_section = f"\n## AI科研信息详情（全部{stats['research_count']}条）\n{research_text}"
        industry_section = f"\n## AI产业信息详情（全部{stats['industry_count']}条）\n{industry_text}"

        # 收集所有实际使用的消息ID
        all_used_ids = governance_ids + research_ids + industry_ids

        # 过滤reference_list，只保留实际使用的消息（保持原序号）
        filtered_reference_list = self._filter_references(reference_list, all_used_ids)

        # 组装完整的user_content
        user_content = f"""{header_text}

{stats_section}
{governance_section}
{research_section}
{industry_section}

{requirements}"""

        # 验证总token数
        total_tokens = system_tokens + self._estimate_tokens(user_content)
        logger.info(f"【AIReportGenerator】实际总tokens: {total_tokens} / {self.MAX_INPUT_TOKENS}")

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]

        return messages, filtered_reference_list

    def _estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量

        简化估算规则：
        - 中文：1字 ≈ 2 tokens
        - 英文/数字：1字符 ≈ 0.25 tokens
        - 符号：按0.5 tokens计算

        Args:
            text: 待估算文本

        Returns:
            估算的token数量
        """
        if not text:
            return 0

        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars

        tokens = chinese_chars * 2 + other_chars * 0.25
        return int(tokens)

    def _format_distribution(self, distribution: Dict[str, int]) -> str:
        """格式化分布数据"""
        if not distribution:
            return "（无数据）"

        lines = []
        for key, count in distribution.items():
            lines.append(f"- {key}: {count}条")
        return "\n".join(lines)

    def _build_message_references(self, messages: List[Dict]) -> tuple[Dict[str, int], List[Dict[str, Any]]]:
        """
        构建消息级引用映射表（每条消息独立编号）

        Args:
            messages: 消息列表

        Returns:
            (message_index, reference_list)
            - message_index: {message_id: 序号}
            - reference_list: [{id, title, source_name, url, published_at}, ...]
        """
        message_index = {}
        reference_list = []

        for idx, msg in enumerate(messages, 1):
            msg_id = msg.get('id', '')

            # 为每条消息分配唯一序号
            message_index[msg_id] = idx

            # 构建引用条目（包含message_id用于后续过滤）
            reference_list.append({
                'id': idx,
                'message_id': msg_id,  # 保存message_id用于过滤
                'title': msg.get('title', '无标题'),
                'source_name': msg.get('source_name', 'unknown'),
                'url': msg.get('url', ''),
                'published_at': msg.get('published_at')
            })

        return message_index, reference_list

    def _filter_references(
        self,
        reference_list: List[Dict[str, Any]],
        used_message_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        过滤未使用的引用（保持原有编号）

        Args:
            reference_list: 原始引用列表（包含所有消息）
            used_message_ids: 实际使用的消息ID列表（按使用顺序）

        Returns:
            filtered_list: 过滤后的引用列表（保持原有序号）
        """
        # 构建message_id到reference的映射
        id_to_ref = {}
        for ref in reference_list:
            id_to_ref[ref['message_id']] = ref

        # 按used_message_ids的顺序重新构建引用列表（保持原有序号）
        filtered_list = []
        used_ids_set = set(used_message_ids)  # 转为集合加速查找

        for ref in reference_list:
            if ref['message_id'] in used_ids_set:
                filtered_list.append(ref)

        logger.info(
            f"【AIReportGenerator】过滤引用：原始{len(reference_list)}条 → 实际使用{len(filtered_list)}条"
        )

        return filtered_list

    def _append_references(self, content: str, reference_list: List[Dict[str, Any]]) -> str:
        """
        在报告内容后添加参考文献列表（每条消息独立编号）

        Args:
            content: LLM生成的报告内容
            reference_list: 引用列表 [{id, title, source_name, url, published_at}, ...]

        Returns:
            添加了参考文献的完整报告
        """
        if not reference_list:
            return content

        # 构建参考文献章节
        references_section = "\n\n---\n\n## 参考文献\n\n"

        for ref in reference_list:
            ref_id = ref['id']
            title = ref['title']
            source_name = ref['source_name']
            url = ref['url']

            # 格式：[1] 文章标题 - 消息源名称
            #      https://example.com
            references_section += f"[{ref_id}] {title} - {source_name}\n"
            if url:
                references_section += f"     {url}\n"
            references_section += "\n"

        return content + references_section

    def _format_messages(
        self,
        messages: List[Dict],
        max_tokens: Optional[int] = None,
        message_index: Optional[Dict[str, int]] = None
    ) -> tuple[str, List[str]]:
        """
        格式化消息列表（带引用序号）

        Args:
            messages: 消息列表
            max_tokens: 最大token数限制（可选），超过则截断
            message_index: 消息序号映射 {message_id: 序号}，用于标注引用

        Returns:
            (formatted_text, used_message_ids)
            - formatted_text: 格式化后的文本
            - used_message_ids: 实际使用的消息ID列表（用于过滤参考文献）
        """
        if not messages:
            return "（无数据）", []

        lines = []
        total_tokens = 0
        used_message_ids = []  # 记录实际使用的消息ID

        for i, msg in enumerate(messages, 1):
            published_at = msg.get('published_at')
            time_str = published_at.strftime('%m-%d %H:%M') if published_at else '未知时间'

            msg_id = msg.get('id', '')
            source_name = msg.get('source_name', 'unknown')

            # 如果提供了message_index，使用消息序号标注；否则使用消息源名称
            if message_index and msg_id in message_index:
                ref_id = message_index[msg_id]
                # 标题行：列表序号 + 引用序号
                line = f"\n{i}. [引用{ref_id}] {msg['title']}"
            else:
                line = f"\n{i}. [{source_name}] {msg['title']}"

            if msg.get('region'):
                line += f" | 地区：{msg['region']}"
            line += f" | {time_str}"

            # 添加摘要或内容（优先使用summary，如果没有则使用content的前500字）
            summary = msg.get('summary') or msg.get('content', '')
            if summary:
                # 限制长度，避免prompt过长
                if len(summary) > 500:
                    summary = summary[:500] + "..."
                line += f"\n   {summary}"

            # 检查token限制
            if max_tokens:
                line_tokens = self._estimate_tokens(line)
                if total_tokens + line_tokens > max_tokens:
                    # 超过限制，停止添加
                    lines.append(f"\n...[消息过多，仅显示前{i-1}条，共{len(messages)}条消息]")
                    logger.warning(
                        f"【AIReportGenerator】消息列表超过token限制 "
                        f"({total_tokens + line_tokens} > {max_tokens})，截断至前{i-1}条"
                    )
                    break
                total_tokens += line_tokens

            lines.append(line)
            used_message_ids.append(msg_id)  # 记录使用的消息ID

        return "\n".join(lines), used_message_ids

    def _build_governance_prompt(
        self,
        messages_by_tag: Dict[str, List[Dict]],
        stats: Dict[str, Any],
        report_date: date
    ) -> tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
        """
        构建AI治理日报提示词（专注政策、法律、监管、伦理，带引用系统）
        """
        # 只获取治理信息
        governance_messages = messages_by_tag.get('AI治理信息', [])
        date_str = report_date.strftime('%Y年%m月%d日')

        # 构建引用映射（每条消息独立编号）
        message_index, reference_list = self._build_message_references(governance_messages)
        logger.info(f"【AIReportGenerator:治理日报】构建了{len(reference_list)}条消息引用")

        system_content = """你是一位专业的AI治理政策分析师，长期跟踪全球AI监管动态、政策演变和伦理讨论。

报告要求：
1. 使用Markdown格式
2. 结构：标题、摘要、重点政策解读、国际对比、趋势判断
3. 语言专业且权威，分析深入透彻
4. 突出政策意图、合规影响、监管趋势
5. 深度解读每个政策事件的背景、目的、影响范围
6. 关注不同国家/地区的监管策略对比
7. 提供合规建议和风险预警
8. 字数不限，以深度和完整性为优先

内容撰写与消息源引用规范（必须严格遵守）：
1. 针对每条新闻深入展开，阐释政策背景、细节、影响等，不要过度压缩
2. 每个事件后必须用方括号标注引用序号，如：[1]、[2]、[1][3]（多个来源）
3. 引用序号对应输入数据中的"引用X"标记，请务必准确匹配
4. 引用格式示例："欧盟AI法案的实施细则进一步明确了高风险AI系统的定义[1][3]，这将对全球AI监管产生示范效应。"
5. 不要在方括号中写消息源名称，只写序号
6. 参考来源列表会由系统自动添加，你不需要在报告中生成
7. 引用尾注不要过于频繁：同一个引用序号在同一个大段落内最多只出现一次，避免重复标注同一来源

客观性与中立性原则：
1. 对涉及中国的负面信息，保持中性和怀疑态度
2. 对带有偏见的描述进行中性过滤和客观改写
3. 多角度呈现信息，提供平衡视角"""

        # 计算固定部分的token数
        system_tokens = self._estimate_tokens(system_content)

        # 构建统计部分
        stats_section = f"""## 统计概览
- 治理信息数量：{len(governance_messages)}条

## 地区分布
{self._format_distribution(stats['region_distribution'])}

## 消息来源
{self._format_distribution(stats['source_distribution'])}"""

        stats_tokens = self._estimate_tokens(stats_section)

        # 要求部分
        requirements = """---

请生成结构化的AI治理日报，包含：

1. **标题**：体现当日核心政策主题

2. **摘要**：3-5段话概括今日治理要点，重点突出：
   - 关键政策动态（发布/修订/生效）
   - 重大监管行动（调查/处罚/约谈）
   - 重要伦理讨论（争议/建议/共识）
   - 国际协调进展（对话/协议/标准）

3. **重点政策解读**：
   - 覆盖所有重要政策事件，逐一深度解读
   - 每个政策分析需包括：
     * 政策背景：为什么在此时发布？
     * 核心条款：主要管制内容和要求
     * 影响范围：涉及哪些企业、行业、技术
     * 合规要求：企业需要采取的行动
     * 监管意图：政府的战略考量

4. **国际对比分析**：
   - 对比不同国家/地区的监管策略差异
   - 分析监管理念的碰撞与融合
   - 识别全球监管的趋势和共性

5. **趋势判断与建议**：
   - 短期趋势：未来3-6个月可能的政策动向
   - 中长期趋势：全球AI治理的演变路径
   - 合规建议：企业应关注的重点领域
   - 风险预警：可能的监管风险点

**分析深度要求**：
- 每个政策事件至少200字的深度分析
- 挖掘政策背后的政治、经济、社会驱动力
- 预判政策执行中可能的难点和争议
- 提供具有可操作性的合规建议"""

        requirements_tokens = self._estimate_tokens(requirements)

        # 计算消息详情可用的token数
        header_text = f"今天是{date_str}，请生成AI治理日报："
        header_tokens = self._estimate_tokens(header_text)

        available_tokens = self.MAX_INPUT_TOKENS - system_tokens - stats_tokens - requirements_tokens - header_tokens

        logger.info(
            f"【AIReportGenerator:治理日报】Token分配 - "
            f"总限制:{self.MAX_INPUT_TOKENS}, "
            f"system:{system_tokens}, "
            f"stats:{stats_tokens}, "
            f"requirements:{requirements_tokens}, "
            f"消息可用:{available_tokens}"
        )

        # 格式化消息详情（带token限制和引用序号），并收集实际使用的消息ID
        messages_text, used_message_ids = self._format_messages(
            governance_messages,
            max_tokens=available_tokens,
            message_index=message_index
        )
        messages_section = f"\n## 治理信息详情（全部{len(governance_messages)}条）\n{messages_text}"

        # 组装完整的user_content
        user_content = f"""{header_text}

{stats_section}
{messages_section}

{requirements}"""

        # 验证总token数
        total_tokens = system_tokens + self._estimate_tokens(user_content)
        logger.info(f"【AIReportGenerator:治理日报】实际总tokens: {total_tokens} / {self.MAX_INPUT_TOKENS}")

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]

        # 过滤引用列表：只保留实际使用的消息
        filtered_reference_list = self._filter_references(reference_list, used_message_ids)

        return messages, filtered_reference_list

    def _build_research_prompt(
        self,
        messages_by_tag: Dict[str, List[Dict]],
        stats: Dict[str, Any],
        report_date: date
    ) -> tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
        """
        构建AI科研日报提示词（专注论文、研究、算法、技术突破，带引用系统）
        """
        # 只获取科研信息
        research_messages = messages_by_tag.get('AI科研信息', [])
        date_str = report_date.strftime('%Y年%m月%d日')

        # 构建引用映射（每条消息独立编号）
        message_index, reference_list = self._build_message_references(research_messages)
        logger.info(f"【AIReportGenerator:科研日报】构建了{len(reference_list)}条消息引用")

        system_content = """你是一位资深的AI技术研究员，专注于前沿AI技术、学术进展和科研趋势。

报告要求：
1. 使用Markdown格式
2. 结构：标题、摘要、重点研究解读、技术分析、学术趋势
3. 语言专业且精确，分析具有技术深度
4. 突出技术创新、方法论突破、学术价值
5. 深度解读每个研究成果的原理、创新点、潜在应用
6. 分析技术演进路径和研究热点
7. 评估学术成果对产业的影响
8. 字数不限，以技术深度为优先

内容撰写与消息源引用规范（必须严格遵守）：
1. 针对每篇论文/研究深入展开技术细节、创新点、实验结果
2. 每个研究后必须用方括号标注引用序号，如：[1]、[2]、[1][3]（多个来源）
3. 引用序号对应输入数据中的"引用X"标记，请务必准确匹配
4. 引用格式示例："研究团队提出了新的注意力机制[1]，在多个基准测试上实现了SOTA性能。"
5. 不要在方括号中写消息源名称，只写序号
6. 参考来源列表会由系统自动添加，你不需要在报告中生成
7. 引用尾注不要过于频繁：同一个引用序号在同一个大段落内最多只出现一次，避免重复标注同一来源

技术准确性原则：
1. 使用准确的技术术语和概念
2. 对复杂技术进行通俗化解释，但不失精确性
3. 客观评价研究的创新性和局限性"""

        # 计算固定部分的token数
        system_tokens = self._estimate_tokens(system_content)

        # 构建统计部分
        stats_section = f"""## 统计概览
- 科研信息数量：{len(research_messages)}条

## 地区分布
{self._format_distribution(stats['region_distribution'])}

## 消息来源
{self._format_distribution(stats['source_distribution'])}"""

        stats_tokens = self._estimate_tokens(stats_section)

        # 要求部分
        requirements = """---

请生成结构化的AI科研日报，包含：

1. **标题**：体现当日核心技术主题

2. **摘要**：3-5段话概括今日科研要点，重点突出：
   - 重大技术突破（新算法/新架构/新方法）
   - 重要论文发布（顶会论文/高引用论文）
   - 关键实验结果（性能提升/新应用场景）
   - 研究热点转移（新兴方向/冷门复兴）

3. **重点研究解读**：
   - 覆盖所有重要研究成果，逐一深度分析
   - 每个研究分析需包括：
     * 研究背景：解决什么问题？为什么重要？
     * 技术原理：核心方法和创新点（用通俗语言解释）
     * 实验结果：性能对比、基准测试、消融实验
     * 创新评价：与已有工作的差异、真正的突破在哪里
     * 潜在应用：可能的产业化方向

4. **技术演进分析**：
   - 追踪技术发展脉络（如从Transformer到最新架构）
   - 识别技术瓶颈和解决路径
   - 预判下一步研究方向

5. **学术趋势与展望**：
   - 当前研究热点：哪些领域最活跃？
   - 冷门复兴：有哪些被重新关注的经典问题？
   - 跨学科融合：AI与其他领域的交叉研究
   - 产学转化：学术成果的工程化潜力

**分析深度要求**：
- 每个研究至少200字的技术解读
- 用5W1H分析：What/Why/How/Who/When/Where
- 区分"真创新"和"边际改进"
- 结合历史研究脉络进行纵向对比"""

        requirements_tokens = self._estimate_tokens(requirements)

        # 计算消息详情可用的token数
        header_text = f"今天是{date_str}，请生成AI科研日报："
        header_tokens = self._estimate_tokens(header_text)

        available_tokens = self.MAX_INPUT_TOKENS - system_tokens - stats_tokens - requirements_tokens - header_tokens

        logger.info(
            f"【AIReportGenerator:科研日报】Token分配 - "
            f"总限制:{self.MAX_INPUT_TOKENS}, "
            f"system:{system_tokens}, "
            f"stats:{stats_tokens}, "
            f"requirements:{requirements_tokens}, "
            f"消息可用:{available_tokens}"
        )

        # 格式化消息详情（带token限制和引用序号），并收集实际使用的消息ID
        messages_text, used_message_ids = self._format_messages(
            research_messages,
            max_tokens=available_tokens,
            message_index=message_index
        )
        messages_section = f"""## 科研信息详情（全部{len(research_messages)}条）
{messages_text}"""

        # 组装完整的user_content
        user_content = f"""{header_text}

{stats_section}
{messages_section}

{requirements}"""

        # 验证总token数
        total_tokens = system_tokens + self._estimate_tokens(user_content)
        logger.info(f"【AIReportGenerator:科研日报】实际总tokens: {total_tokens} / {self.MAX_INPUT_TOKENS}")

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]

        # 过滤引用列表：只保留实际使用的消息
        filtered_reference_list = self._filter_references(reference_list, used_message_ids)

        return messages, filtered_reference_list

    def _build_industry_prompt(
        self,
        messages_by_tag: Dict[str, List[Dict]],
        stats: Dict[str, Any],
        report_date: date
    ) -> tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
        """
        构建AI产业日报提示词（专注企业、投资、产品、应用、商业动态，带引用系统）
        """
        # 只获取产业信息
        industry_messages = messages_by_tag.get('AI产业信息', [])
        date_str = report_date.strftime('%Y年%m月%d日')

        # 构建引用映射（每条消息独立编号）
        message_index, reference_list = self._build_message_references(industry_messages)
        logger.info(f"【AIReportGenerator:产业日报】构建了{len(reference_list)}条消息引用")

        system_content = """你是一位资深的AI产业分析师和投资顾问，专注于AI商业化、市场动态和投资趋势。

报告要求：
1. 使用Markdown格式
2. 结构：标题、摘要、重点商业事件、市场分析、投资趋势
3. 语言专业且商业化，分析具有商业洞察
4. 突出商业模式、投资回报、竞争格局
5. 深度剖析每个商业事件的战略意义、市场影响、财务逻辑
6. 分析企业战略、投资趋势、产业链变化
7. 评估商业机会和投资风险
8. 字数不限，以商业洞察为优先

内容撰写与消息源引用规范（必须严格遵守）：
1. 针对每条商业新闻深入展开战略分析、财务分析、竞争分析
2. 每个事件后必须用方括号标注引用序号，如：[1]、[2]、[1][3]（多个来源）
3. 引用序号对应输入数据中的"引用X"标记，请务必准确匹配
4. 引用格式示例："OpenAI最新一轮融资估值达到1000亿美元[1]，这标志着投资者对通用人工智能（AGI）商业化前景的强烈信心。"
5. 不要在方括号中写消息源名称，只写序号
6. 参考来源列表会由系统自动添加，你不需要在报告中生成
7. 引用尾注不要过于频繁：同一个引用序号在同一个大段落内最多只出现一次，避免重复标注同一来源

内容优先级原则：
1. 最新发布的AI模型是时效性最高的内容，应作为最重要的事件优先报道和深度分析
2. 模型发布相关新闻（如GPT、Claude、Gemini、Llama等新版本）应放在显著位置，详细分析其技术突破、商业意义和行业影响

商业客观性原则：
1. 区分公司公关稿和实质性商业新闻
2. 客观评价商业决策的合理性和风险
3. 提供基于数据的分析，而非主观判断"""

        # 计算固定部分的token数
        system_tokens = self._estimate_tokens(system_content)

        # 构建统计部分
        stats_section = f"""## 统计概览
- 产业信息数量：{len(industry_messages)}条

## 地区分布
{self._format_distribution(stats['region_distribution'])}

## 消息来源
{self._format_distribution(stats['source_distribution'])}"""

        stats_tokens = self._estimate_tokens(stats_section)

        # 要求部分
        requirements = """---

请生成结构化的AI产业日报，包含：

1. **标题**：体现当日核心商业主题

2. **摘要**：3-5段话概括今日产业要点，重点突出：
   - 重大投融资事件（大额融资/IPO/并购）
   - 关键产品发布（新模型/新应用/新服务）
   - 重要战略决策（合作/转型/裁员）
   - 市场格局变化（份额转移/新玩家入场）

3. **重点商业事件分析**：
   - 覆盖所有重要商业事件，逐一深度分析
   - 每个事件分析需包括：
     * 事件背景：公司当前状态、市场环境
     * 战略意图：为什么做这个决策？
     * 商业逻辑：盈利模式、成本结构、增长预期
     * 竞争影响：对竞争对手、产业链的影响
     * 风险评估：可能的执行风险和市场风险

4. **市场竞争格局**：
   - 主要玩家的战略对比（OpenAI vs Anthropic vs Google等）
   - 市场份额变化和增长动力
   - 新进入者的差异化策略
   - 产业链价值分配（芯片-模型-应用）

5. **投资趋势与机会**：
   - 热门赛道：哪些细分领域最受资本青睐？
   - 估值逻辑：投资者如何评估AI公司价值？
   - 商业化路径：成功的商业模式有哪些共性？
   - 投资建议：值得关注的机会和需要规避的风险

**分析深度要求**：
- 每个事件至少200字的商业分析
- 用Porter五力模型分析竞争格局
- 结合财务数据进行量化分析
- 提供具有可操作性的投资建议"""

        requirements_tokens = self._estimate_tokens(requirements)

        # 计算消息详情可用的token数
        header_text = f"今天是{date_str}，请生成AI产业日报："
        header_tokens = self._estimate_tokens(header_text)

        available_tokens = self.MAX_INPUT_TOKENS - system_tokens - stats_tokens - requirements_tokens - header_tokens

        logger.info(
            f"【AIReportGenerator:产业日报】Token分配 - "
            f"总限制:{self.MAX_INPUT_TOKENS}, "
            f"system:{system_tokens}, "
            f"stats:{stats_tokens}, "
            f"requirements:{requirements_tokens}, "
            f"消息可用:{available_tokens}"
        )

        # 格式化消息详情（带token限制和引用序号），并收集实际使用的消息ID
        messages_text, used_message_ids = self._format_messages(
            industry_messages,
            max_tokens=available_tokens,
            message_index=message_index
        )
        messages_section = f"""## 产业信息详情（全部{len(industry_messages)}条）
{messages_text}"""

        # 组装完整的user_content
        user_content = f"""{header_text}

{stats_section}
{messages_section}

{requirements}"""

        # 验证总token数
        total_tokens = system_tokens + self._estimate_tokens(user_content)
        logger.info(f"【AIReportGenerator:产业日报】实际总tokens: {total_tokens} / {self.MAX_INPUT_TOKENS}")

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]

        # 过滤引用列表：只保留实际使用的消息
        filtered_reference_list = self._filter_references(reference_list, used_message_ids)

        return messages, filtered_reference_list

    async def _generate_report_content(
        self,
        messages_by_tag: Dict[str, List[Dict]],
        stats: Dict[str, Any],
        report_date: date
    ) -> str:
        """
        调用LLM生成报告内容（带引用系统）

        Args:
            messages_by_tag: 按标签分类的消息
            stats: 统计数据
            report_date: 报告日期

        Returns:
            生成的报告内容（Markdown格式，包含参考来源）
        """
        llm_client = self._get_llm_client()
        messages, reference_list = self._build_report_prompt(messages_by_tag, stats, report_date)

        try:
            logger.info("【AIReportGenerator】调用LLM生成报告...")

            # 异步调用LLM（输入限制88K，输出空间由API自动计算）
            response = await llm_client.generate_with_messages_async(
                messages,
                source="AIReportGenerator:comprehensive"
            )

            # 提取生成的内容
            if hasattr(response, 'choices') and len(response.choices) > 0:
                content = response.choices[0].message.content
                logger.info(f"【AIReportGenerator】报告生成成功（长度：{len(content)}字符）")

                # 后处理：添加参考来源列表
                final_content = self._append_references(content, reference_list)
                logger.info(f"【AIReportGenerator】添加了{len(reference_list)}个参考来源")

                return final_content
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

    async def _generate_governance_report_content(
        self,
        messages_by_tag: Dict[str, List[Dict]],
        stats: Dict[str, Any],
        report_date: date
    ) -> str:
        """
        生成AI治理日报内容（带引用系统）

        专注于政策、法律、监管、伦理相关内容
        """
        llm_client = self._get_llm_client()
        messages, reference_list = self._build_governance_prompt(messages_by_tag, stats, report_date)

        try:
            logger.info("【AIReportGenerator】调用LLM生成治理日报...")
            response = await llm_client.generate_with_messages_async(
                messages,
                source="AIReportGenerator:governance"
            )

            if hasattr(response, 'choices') and len(response.choices) > 0:
                content = response.choices[0].message.content
                logger.info(f"【AIReportGenerator】治理日报生成成功（长度：{len(content)}字符）")

                # 后处理：添加参考来源列表
                final_content = self._append_references(content, reference_list)
                logger.info(f"【AIReportGenerator:治理日报】添加了{len(reference_list)}个参考来源")

                return final_content
            else:
                raise ValueError("LLM返回格式异常")

        except Exception as e:
            logger.error(f"【AIReportGenerator】治理日报生成失败: {e}", exc_info=True)
            return self._generate_fallback_report(stats)

    async def _generate_research_report_content(
        self,
        messages_by_tag: Dict[str, List[Dict]],
        stats: Dict[str, Any],
        report_date: date
    ) -> str:
        """
        生成AI科研日报内容（带引用系统）

        专注于论文、研究、算法、技术突破相关内容
        """
        llm_client = self._get_llm_client()
        messages, reference_list = self._build_research_prompt(messages_by_tag, stats, report_date)

        try:
            logger.info("【AIReportGenerator】调用LLM生成科研日报...")
            response = await llm_client.generate_with_messages_async(
                messages,
                source="AIReportGenerator:research"
            )

            if hasattr(response, 'choices') and len(response.choices) > 0:
                content = response.choices[0].message.content
                logger.info(f"【AIReportGenerator】科研日报生成成功（长度：{len(content)}字符）")

                # 后处理：添加参考来源列表
                final_content = self._append_references(content, reference_list)
                logger.info(f"【AIReportGenerator:科研日报】添加了{len(reference_list)}个参考来源")

                return final_content
            else:
                raise ValueError("LLM返回格式异常")

        except Exception as e:
            logger.error(f"【AIReportGenerator】科研日报生成失败: {e}", exc_info=True)
            return self._generate_fallback_report(stats)

    async def _generate_industry_report_content(
        self,
        messages_by_tag: Dict[str, List[Dict]],
        stats: Dict[str, Any],
        report_date: date
    ) -> str:
        """
        生成AI产业日报内容（带引用系统）

        专注于企业、投资、产品、应用、商业动态相关内容
        """
        llm_client = self._get_llm_client()
        messages, reference_list = self._build_industry_prompt(messages_by_tag, stats, report_date)

        try:
            logger.info("【AIReportGenerator】调用LLM生成产业日报...")
            response = await llm_client.generate_with_messages_async(
                messages,
                source="AIReportGenerator:industry"
            )

            if hasattr(response, 'choices') and len(response.choices) > 0:
                content = response.choices[0].message.content
                logger.info(f"【AIReportGenerator】产业日报生成成功（长度：{len(content)}字符）")

                # 后处理：添加参考来源列表
                final_content = self._append_references(content, reference_list)
                logger.info(f"【AIReportGenerator:产业日报】添加了{len(reference_list)}个参考来源")

                return final_content
            else:
                raise ValueError("LLM返回格式异常")

        except Exception as e:
            logger.error(f"【AIReportGenerator】产业日报生成失败: {e}", exc_info=True)
            return self._generate_fallback_report(stats)

    async def generate_daily_report(
        self,
        report_date: Optional[datetime] = None,
        report_type: str = 'comprehensive'
    ) -> Optional[str]:
        """
        生成每日报告

        Args:
            report_date: 报告日期（datetime或date类型，默认为今天）
            report_type: 报告类型（comprehensive/governance/research/industry）

        Returns:
            报告ID（UUID），失败返回None
        """
        # 统一转换为date类型
        if report_date is None:
            report_date = datetime.now().date()
        elif isinstance(report_date, datetime):
            report_date = report_date.date()

        report_type_names = {
            'comprehensive': '综合日报',
            'governance': '治理日报',
            'research': '科研日报',
            'industry': '产业日报'
        }
        report_name = report_type_names.get(report_type, report_type)

        logger.info(f"【AIReportGenerator】开始生成{report_date}的{report_name}")

        try:
            with create_session() as db:
                # 检查是否已存在报告（同日期+同类型）
                existing_report = db.query(AIDailyReport).filter(
                    and_(
                        AIDailyReport.report_date == report_date,
                        AIDailyReport.report_type == report_type
                    )
                ).first()

                if existing_report:
                    logger.warning(f"【AIReportGenerator】{report_date}的{report_name}已存在（ID: {existing_report.id}）")
                    return existing_report.id

                # 根据报告类型确定ai_tag过滤器
                ai_tag_filter_map = {
                    'comprehensive': None,  # 综合报告收集所有
                    'governance': 'AI治理信息',
                    'research': 'AI科研信息',
                    'industry': 'AI产业信息'
                }
                ai_tag_filter = ai_tag_filter_map.get(report_type)

                # 收集消息（根据类型过滤）
                messages_by_tag = self._collect_messages_from_last_24h(db, report_date, ai_tag_filter)

                # 聚合统计
                stats = self._aggregate_statistics(messages_by_tag)

                # 检查是否有数据
                if stats['total_messages'] == 0:
                    logger.warning(f"【AIReportGenerator】{report_name}无消息数据，跳过报告生成")
                    return None

                # 根据报告类型选择不同的提示词构建方法
                if report_type == 'governance':
                    report_content = await self._generate_governance_report_content(messages_by_tag, stats, report_date)
                elif report_type == 'research':
                    report_content = await self._generate_research_report_content(messages_by_tag, stats, report_date)
                elif report_type == 'industry':
                    report_content = await self._generate_industry_report_content(messages_by_tag, stats, report_date)
                else:  # comprehensive
                    report_content = await self._generate_report_content(messages_by_tag, stats, report_date)

                # 保存到数据库
                report_id = str(uuid.uuid4())
                report = AIDailyReport(
                    id=report_id,
                    report_date=report_date,
                    report_type=report_type,
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
                        report_type=report_type,
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

    async def generate_governance_report(self, report_date: Optional[datetime] = None) -> Optional[str]:
        """
        生成AI治理日报

        Args:
            report_date: 报告日期（默认为今天）

        Returns:
            报告ID（UUID），失败返回None
        """
        return await self.generate_daily_report(report_date, report_type='governance')

    async def generate_research_report(self, report_date: Optional[datetime] = None) -> Optional[str]:
        """
        生成AI科研日报

        Args:
            report_date: 报告日期（默认为今天）

        Returns:
            报告ID（UUID），失败返回None
        """
        return await self.generate_daily_report(report_date, report_type='research')

    async def generate_industry_report(self, report_date: Optional[datetime] = None) -> Optional[str]:
        """
        生成AI产业日报

        Args:
            report_date: 报告日期（默认为今天）

        Returns:
            报告ID（UUID），失败返回None
        """
        return await self.generate_daily_report(report_date, report_type='industry')


# 全局单例
_report_generator = None


def get_report_generator() -> AIReportGenerator:
    """获取全局日报生成器实例"""
    global _report_generator
    if _report_generator is None:
        _report_generator = AIReportGenerator()
    return _report_generator
