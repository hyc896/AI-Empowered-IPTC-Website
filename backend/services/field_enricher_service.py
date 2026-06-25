33# -*- coding: utf-8 -*-

"""
字段增强服务
为消息添加region（地区）和industry_tags（行业标签）字段

功能特性：
- 自动地区分类（国家/省份/城市，斜杠分隔）
- 自动行业标签分类（28个标准行业，逗号分隔，最多3个）
- 并发控制（防止API过载）
- 自动重试机制（指数退避）
- 降级策略（分类失败时返回NULL）
- 批量处理优化
- 网络错误优雅降级（不刷屏）
"""

import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Optional, List, Dict

# 网络错误类型（用于优雅降级）
try:
    from openai import APIConnectionError
    import httpx
    NETWORK_ERRORS = (APIConnectionError, httpx.ConnectError, httpx.TimeoutException, ConnectionError, OSError)
except ImportError:
    NETWORK_ERRORS = (ConnectionError, OSError)

logger = logging.getLogger(__name__)


class FieldEnricherService:
    """
    字段增强服务

    使用Fast LLM模型为消息添加region和industry_tags字段
    """

    def __init__(
        self,
        max_concurrent: int = 2,
        max_retries: int = 3,
        timeout: int = 30
    ):
        """
        初始化字段增强服务

        Args:
            max_concurrent: 最大并发数（默认2）
            max_retries: 最大重试次数（默认3）
            timeout: 单次请求超时时间（秒，默认30）
        """
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.timeout = timeout

        # 并发控制信号量
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # 延迟加载LLM客户端（避免循环导入）
        self._llm_client = None

        # 延迟加载EventBus（避免循环导入）
        self._event_bus = None

        # 429错误追踪（TPM限流）
        self._consecutive_429_count = 0  # 连续429错误计数
        self._total_429_count = 0  # 总429错误计数
        self._backoff_seconds = 0  # 当前退避等待时间

        # 网络错误追踪（避免重复打印）
        self._network_error_logged = False  # 是否已打印过网络错误

    def _get_llm_client(self):
        """延迟加载Fast LLM客户端"""
        if self._llm_client is None:
            from backend.llm import get_fast_client
            self._llm_client = get_fast_client()

            if self._llm_client is None:
                logger.error("【FieldEnricher】Fast LLM客户端未初始化")
                raise RuntimeError("Fast LLM client not initialized")

        return self._llm_client

    def _get_event_bus(self):
        """延迟加载EventBus实例"""
        if self._event_bus is None:
            from backend.services.event_bus import get_event_bus
            self._event_bus = get_event_bus()
        return self._event_bus

    async def _publish_ai_tag_event(self, data: dict):
        """
        发布AI标签事件（内部方法）

        设计原则：
        - 失败不抛异常，仅记录日志
        - 使用fire-and-forget模式
        - 不阻塞主流程
        """
        try:
            event_bus = self._get_event_bus()
            await event_bus.publish("new_ai_message", data)
            logger.debug(f"事件已发布: {data['ai_tag']} - {data['title'][:30]}")
        except Exception as e:
            # 事件发布失败不影响主流程
            logger.warning(f"事件发布失败: {e}", exc_info=False)

    def _is_network_error(self, error: Exception) -> bool:
        """
        检测是否为网络连接错误

        Args:
            error: 异常对象

        Returns:
            是否为网络错误
        """
        # 直接检查异常类型
        if isinstance(error, NETWORK_ERRORS):
            return True

        # 检查错误消息
        error_str = str(error).lower()
        return (
            "connection error" in error_str or
            "connect error" in error_str or
            "connection refused" in error_str or
            "network is unreachable" in error_str or
            "all connection attempts failed" in error_str
        )

    def _handle_network_error(self, context: str) -> None:
        """
        处理网络错误（只打印一次警告）

        Args:
            context: 上下文描述（如"地区分类"、"行业分类"）
        """
        if not self._network_error_logged:
            logger.warning(f"【FieldEnricher】网络连接失败，{context}跳过（检查VPN/代理）")
            self._network_error_logged = True

    def _reset_network_error_flag(self) -> None:
        """网络恢复后重置标志"""
        if self._network_error_logged:
            logger.info("【FieldEnricher】网络已恢复")
            self._network_error_logged = False

    def _strip_scalar_response(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        value = value.strip().strip('`').strip().strip('"“”\'')
        value = re.sub(r'^(地区|区域|region|标签|分类)\s*[:：]\s*', '', value, flags=re.I)
        return value.strip().strip('"“”\'') or None

    def _contains_explanation(self, value: str) -> bool:
        explanation_markers = (
            '\n', '根据', '分析', '因此', '所以', '标题：', '内容：', '格式：',
            '规则', '您提供', '我将', '可以标注', '返回', '输出'
        )
        return any(marker in value for marker in explanation_markers)

    def _clean_region(self, value: Optional[str]) -> Optional[str]:
        value = self._strip_scalar_response(value)
        if not value or self._contains_explanation(value) or len(value) > 40:
            return None
        value = value.replace(' / ', '/').replace('／', '/').replace('\\', '/')
        value = re.sub(r'\s+', '/', value)
        if self._is_invalid_region(value):
            return None
        return value

    def _clean_industry_tags(self, value: Optional[str]) -> Optional[str]:
        value = self._strip_scalar_response(value)
        if not value or self._contains_explanation(value) or len(value) > 80:
            return None
        value = value.replace('，', ',').replace('、', ',').replace('；', ',')
        aliases = {
            '半导体芯片': '半导体/芯片',
            '航空制造': '航空航天',
            'aerospace': '航空航天',
            '其他其他行业': '其他行业',
        }
        normalized = []
        for tag in [tag.strip().strip('"“”\'') for tag in value.split(',') if tag.strip()]:
            tag = aliases.get(tag, tag)
            if len(tag) <= 12 and tag not in normalized:
                normalized.append(tag)
        return ','.join(normalized[:3]) if normalized else None

    def _clean_ai_tag(self, value: Optional[str]) -> Optional[str]:
        value = self._strip_scalar_response(value)
        if not value or self._contains_explanation(value):
            return None
        valid_tags = ["AI科研信息", "AI产业信息", "AI治理信息"]
        for tag in valid_tags:
            if tag in value:
                return tag
        return None

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """
        检测是否为429速率限制错误

        Args:
            error: 异常对象

        Returns:
            是否为429错误
        """
        error_str = str(error).lower()
        return (
            "429" in error_str or
            "rate limit" in error_str or
            "too many requests" in error_str or
            "quota exceeded" in error_str
        )

    async def _handle_rate_limit(self):
        """
        处理429速率限制错误（固定等待）

        每次遇到429：
        - 连续计数+1
        - 统一等待60秒
        """
        self._consecutive_429_count += 1
        self._total_429_count += 1

        # 固定等待60秒
        self._backoff_seconds = 60

        logger.warning(
            f"【FieldEnricher】检测到TPM限流（429错误）"
            f"[连续{self._consecutive_429_count}次，总计{self._total_429_count}次]，"
            f"等待{self._backoff_seconds}秒后继续..."
        )

        await asyncio.sleep(self._backoff_seconds)

    def _reset_rate_limit_counter(self):
        """成功调用后重置连续429计数器"""
        if self._consecutive_429_count > 0:
            logger.info(
                f"【FieldEnricher】API调用成功，重置连续429计数器"
                f"（之前连续{self._consecutive_429_count}次）"
            )
            self._consecutive_429_count = 0
            self._backoff_seconds = 0

    async def enrich_fields(
        self,
        title: str,
        content: str,
        message_id: str = None,
        source_name: str = None
    ) -> Dict[str, Optional[str]]:
        """
        增强字段（单条消息）

        先并发执行地区分类和行业分类，仅当industry_tags包含"人工智能"时才执行AI标签分类

        Args:
            title: 消息标题
            content: 消息内容
            message_id: 消息ID（用于事件携带，可选）
            source_name: 消息源名称（用于事件携带，可选）

        Returns:
            字典包含：
            - region: 地区（如"中国/广东省/深圳市"）
            - industry_tags: 行业标签（如"人工智能,半导体"）
            - ai_tag: AI分类标签（"AI科研信息"/"AI产业信息"/"AI治理信息"），仅在包含"人工智能"标签时返回
            失败时对应字段为None
        """
        if not title or not content:
            logger.warning("【FieldEnricher】标题或内容为空，跳过增强")
            return {"region": None, "industry_tags": None, "ai_tag": None}

        # 串行执行地区分类和行业分类
        # 注意：在Celery solo pool + nest_asyncio环境下，asyncio.gather会导致任务上下文混乱
        # 错误表现："RuntimeError: Leaving task does not match the current task"
        # 因此改为串行执行，牺牲少量性能换取稳定性
        region = await self._classify_region(title, content)
        industry_tags = await self._classify_industry(title, content)

        # 第二步：检查industry_tags是否包含"人工智能"，决定是否执行ai_tag分类
        ai_tag = None
        if industry_tags and "人工智能" in industry_tags:
            logger.debug(f"【FieldEnricher】检测到'人工智能'标签，执行AI分类")
            ai_tag = await self._classify_ai_tag(title, content)

            # 如果生成了ai_tag，异步发布事件（fire-and-forget）
            if ai_tag and message_id:
                asyncio.create_task(self._publish_ai_tag_event({
                    "message_id": message_id,
                    "title": title,
                    "summary": content[:200] + "..." if len(content) > 200 else content,
                    "ai_tag": ai_tag,
                    "source_name": source_name or "未知",
                    "timestamp": datetime.now().isoformat()
                }))
        else:
            logger.debug(f"【FieldEnricher】未检测到'人工智能'标签（industry_tags={industry_tags}），跳过AI分类")

        return {
            "region": region,
            "industry_tags": industry_tags,
            "ai_tag": ai_tag
        }

    async def enrich_batch(
        self,
        messages: List[Dict[str, str]],
        show_progress: bool = False
    ) -> List[Dict[str, Optional[str]]]:
        """
        批量增强字段（串行执行）

        注意：在Celery solo pool + nest_asyncio环境下，asyncio.gather/as_completed会导致任务上下文混乱。
        因此改为串行执行，牺牲并发性能换取稳定性。

        Args:
            messages: 消息列表，每条包含title和content
            show_progress: 是否显示进度日志

        Returns:
            增强结果列表（与输入顺序对应）
        """
        if not messages:
            return []

        logger.info(f"【FieldEnricher】开始批量增强: {len(messages)}条消息")

        # 串行执行（避免solo pool模式下的任务上下文冲突）
        results = []
        for i, msg in enumerate(messages, 1):
            result = await self.enrich_fields(msg.get('title', ''), msg.get('content', ''))
            results.append(result)
            if show_progress and (i % 10 == 0 or i == len(messages)):
                logger.info(f"【FieldEnricher】批量增强进度: {i}/{len(messages)}")

        return results

    async def _classify_region(
        self,
        title: str,
        content: str
    ) -> Optional[str]:
        """
        地区分类

        Args:
            title: 消息标题
            content: 消息内容

        Returns:
            地区字符串（如"中国/广东省/深圳市"），失败返回None
        """
        async with self._semaphore:
            max_429_retries = 10  # 最多连续10次429错误后放弃
            consecutive_429_in_this_call = 0

            for attempt in range(self.max_retries):
                try:
                    logger.debug(
                        f"【FieldEnricher】地区分类 "
                        f"(尝试{attempt + 1}/{self.max_retries}, "
                        f"并发: {self.max_concurrent - self._semaphore._value}/{self.max_concurrent})"
                    )

                    # 构建Prompt
                    prompt = self._build_region_prompt(title, content)

                    # 调用Fast LLM
                    llm_client = self._get_llm_client()
                    response = await asyncio.wait_for(
                        llm_client.generate_with_messages_async(
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=80,
                            source="FieldEnricher:region"
                        ),
                        timeout=self.timeout
                    )

                    raw_region = response.choices[0].message.content.strip()
                    region = self._clean_region(raw_region)

                    # 验证格式：短地区值，不包含解释性文本
                    if region:
                        logger.debug(f"【FieldEnricher】地区分类成功: {region}")
                        self._reset_rate_limit_counter()  # 成功则重置429计数
                        return region
                    else:
                        logger.warning(f"【FieldEnricher】地区分类结果格式异常: {raw_region}")
                        return None

                except Exception as e:
                    # 优先检测网络错误（直接返回None，不重试，不刷屏）
                    if self._is_network_error(e):
                        self._handle_network_error("地区分类")
                        return None

                    # 检测429错误
                    if self._is_rate_limit_error(e):
                        consecutive_429_in_this_call += 1
                        if consecutive_429_in_this_call >= max_429_retries:
                            logger.error(
                                f"【FieldEnricher】连续{max_429_retries}次遇到429错误，放弃本次调用"
                            )
                            return None

                        await self._handle_rate_limit()
                        # 429错误不计入重试次数，继续下一次尝试
                        continue

                    # 其他错误按正常重试逻辑
                    if attempt < self.max_retries - 1:
                        retry_delay = 2 ** attempt
                        logger.warning(
                            f"【FieldEnricher】地区分类失败 "
                            f"(尝试{attempt + 1}/{self.max_retries}): {e}，"
                            f"{retry_delay}秒后重试..."
                        )
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error(f"【FieldEnricher】地区分类所有重试均失败: {e}")
                        return None

    async def _classify_industry(
        self,
        title: str,
        content: str
    ) -> Optional[str]:
        """
        行业标签分类

        Args:
            title: 消息标题
            content: 消息内容

        Returns:
            行业标签字符串（如"人工智能,半导体"），失败返回None
        """
        async with self._semaphore:
            max_429_retries = 10  # 最多连续10次429错误后放弃
            consecutive_429_in_this_call = 0

            for attempt in range(self.max_retries):
                try:
                    logger.debug(
                        f"【FieldEnricher】行业分类 "
                        f"(尝试{attempt + 1}/{self.max_retries}, "
                        f"并发: {self.max_concurrent - self._semaphore._value}/{self.max_concurrent})"
                    )

                    # 构建Prompt
                    prompt = self._build_industry_prompt(title, content)

                    # 调用Fast LLM
                    llm_client = self._get_llm_client()
                    response = await asyncio.wait_for(
                        llm_client.generate_with_messages_async(
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=80,
                            source="FieldEnricher:industry"
                        ),
                        timeout=self.timeout
                    )

                    raw_tags = response.choices[0].message.content.strip()
                    tags = self._clean_industry_tags(raw_tags)

                    # 验证格式：逗号分隔，最多3个短标签
                    if tags:
                        logger.debug(f"【FieldEnricher】行业分类成功: {tags}")
                        self._reset_rate_limit_counter()  # 成功则重置429计数
                        return tags
                    else:
                        logger.warning(f"【FieldEnricher】行业分类结果格式异常: {raw_tags}")
                        return None

                except Exception as e:
                    # 优先检测网络错误（直接返回None，不重试，不刷屏）
                    if self._is_network_error(e):
                        self._handle_network_error("行业分类")
                        return None

                    # 检测429错误
                    if self._is_rate_limit_error(e):
                        consecutive_429_in_this_call += 1
                        if consecutive_429_in_this_call >= max_429_retries:
                            logger.error(
                                f"【FieldEnricher】连续{max_429_retries}次遇到429错误，放弃本次调用"
                            )
                            return None

                        await self._handle_rate_limit()
                        # 429错误不计入重试次数，继续下一次尝试
                        continue

                    # 其他错误按正常重试逻辑
                    if attempt < self.max_retries - 1:
                        retry_delay = 2 ** attempt
                        logger.warning(
                            f"【FieldEnricher】行业分类失败 "
                            f"(尝试{attempt + 1}/{self.max_retries}): {e}，"
                            f"{retry_delay}秒后重试..."
                        )
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error(f"【FieldEnricher】行业分类所有重试均失败: {e}")
                        return None

    def _build_region_prompt(self, title: str, content: str) -> str:
        """
        构建地区分类Prompt

        Args:
            title: 消息标题
            content: 消息内容

        Returns:
            Prompt字符串
        """
        # 截取content前500字符（避免超长）
        content_excerpt = content[:500] if len(content) > 500 else content

        prompt = f"""判断新闻事件的物理发生地（而非参与方）。

规则：
1. 会议/访问：标注举办地
2. 政策发布：标注发布机构所在地
3. 企业投资：标注投资目的地
4. 组织决议：标注组织总部（欧盟→比利时/布鲁塞尔，联合国→美国/纽约州/纽约市，世贸组织→瑞士/日内瓦）
5. 全球市场：标注"全球"

格式：国家级"国家名"，省级"国家/省份"，市级"国家/省份/城市"

示例：
- "外交部在北京回应" → "中国/北京市"
- "欧盟通过AI法案" → "比利时/布鲁塞尔"
- "Anthropic在美投资" → "美国"
- "国际油价上涨" → "全球"

标题：{title}
内容：{content_excerpt}

仅返回地区（如"中国/北京市"），无解释。"""

        return prompt

    def _build_industry_prompt(self, title: str, content: str) -> str:
        """
        构建行业标签分类Prompt

        Args:
            title: 消息标题
            content: 消息内容

        Returns:
            Prompt字符串
        """
        # 截取content前500字符（避免超长）
        content_excerpt = content[:500] if len(content) > 500 else content

        prompt = f"""为新闻选择行业标签（最多3个，逗号分隔）。

可选标签：人工智能、半导体/芯片、计算机软件、通信设备、电子元器件、互联网服务、新能源/电动车、生物医药、医疗器械、金融科技、汽车制造、机械设备、化工材料、钢铁有色、能源采掘、电力公用、房地产建筑、交通运输、商贸零售、消费品、农林牧渔、传媒娱乐、教育培训、金融服务、环保工程、航空航天、国防军工、其他行业

规则：
1. 涉及AI/大模型/机器学习/深度学习/神经网络，必须含"人工智能"
2. 只标注行业，不标注事件类型（融资/并购等）
3. 无法判断时选"其他行业"

示例：
- "Anthropic投资数据中心" → "人工智能"
- "英伟达发布AI芯片" → "人工智能,半导体/芯片"
- "黄金价格上涨" → "其他行业"

标题：{title}
内容：{content_excerpt}

仅返回标签（如"人工智能,半导体/芯片"），无解释。"""

        return prompt

    async def _classify_ai_tag(
        self,
        title: str,
        content: str
    ) -> Optional[str]:
        """
        AI标签分类

        Args:
            title: 消息标题
            content: 消息内容

        Returns:
            AI标签字符串（"AI科研信息"/"AI产业信息"/"AI治理信息"），失败返回None
        """
        async with self._semaphore:
            max_429_retries = 10
            consecutive_429_in_this_call = 0

            for attempt in range(self.max_retries):
                try:
                    logger.debug(
                        f"【FieldEnricher】AI标签分类 "
                        f"(尝试{attempt + 1}/{self.max_retries}, "
                        f"并发: {self.max_concurrent - self._semaphore._value}/{self.max_concurrent})"
                    )

                    # 构建Prompt
                    prompt = self._build_ai_tag_prompt(title, content)

                    # 调用Fast LLM
                    llm_client = self._get_llm_client()
                    response = await asyncio.wait_for(
                        llm_client.generate_with_messages_async(
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=40,
                            source="FieldEnricher:ai_tag"
                        ),
                        timeout=self.timeout
                    )

                    raw_tag = response.choices[0].message.content.strip()
                    tag = self._clean_ai_tag(raw_tag)

                    # 验证格式：必须是三个标签之一
                    if tag:
                        logger.debug(f"【FieldEnricher】AI标签分类成功: {tag}")
                        self._reset_rate_limit_counter()
                        return tag
                    else:
                        logger.warning(f"【FieldEnricher】AI标签分类结果异常: {raw_tag}")
                        return None

                except Exception as e:
                    # 优先检测网络错误（直接返回None，不重试，不刷屏）
                    if self._is_network_error(e):
                        self._handle_network_error("AI标签分类")
                        return None

                    # 检测429错误
                    if self._is_rate_limit_error(e):
                        consecutive_429_in_this_call += 1
                        if consecutive_429_in_this_call >= max_429_retries:
                            logger.error(
                                f"【FieldEnricher】连续{max_429_retries}次遇到429错误，放弃本次调用"
                            )
                            return None

                        await self._handle_rate_limit()
                        continue

                    # 其他错误按正常重试逻辑
                    if attempt < self.max_retries - 1:
                        retry_delay = 2 ** attempt
                        logger.warning(
                            f"【FieldEnricher】AI标签分类失败 "
                            f"(尝试{attempt + 1}/{self.max_retries}): {e}，"
                            f"{retry_delay}秒后重试..."
                        )
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error(f"【FieldEnricher】AI标签分类所有重试均失败: {e}")
                        return None

    def _build_ai_tag_prompt(self, title: str, content: str) -> str:
        """
        构建AI标签分类Prompt

        Args:
            title: 消息标题
            content: 消息内容

        Returns:
            Prompt字符串
        """
        # 截取content前500字符
        content_excerpt = content[:500] if len(content) > 500 else content

        prompt = f"""将AI新闻分类为三类之一（按优先级判断）：

1. AI治理信息（最高优先级）- 关键词：政策、法律、监管、伦理、安全、隐私、标准
2. AI科研信息 - 关键词：论文、研究、算法、模型、技术突破、arXiv
3. AI产业信息（默认） - 关键词：企业、投资、产品、应用、数据中心

规则：涉及多个类别时优先选治理，无法判断时选产业。

示例：
- "欧盟通过AI法案" → "AI治理信息"
- "清华发表大模型论文" → "AI科研信息"
- "Anthropic投资数据中心" → "AI产业信息"

标题：{title}
内容：{content_excerpt}

仅返回分类（"AI治理信息"/"AI科研信息"/"AI产业信息"），无解释。"""

        return prompt

    def _is_invalid_region(self, region: str) -> bool:
        """
        检测地区分类结果是否无效

        Args:
            region: 地区字符串

        Returns:
            是否无效
        """
        # 检测是否包含异常文本（类似幻觉检测）
        invalid_patterns = [
            "请提供",
            "我将为您",
            "以下是",
            "分析结果",
            "地区：",
            "Region:",
            "无法判断",
            "未知"
        ]

        for pattern in invalid_patterns:
            if pattern in region:
                logger.warning(f"【FieldEnricher】地区分类包含异常文本: {pattern}")
                return True

        return False


# 全局单例（已废弃：在Celery solo pool模式下会导致asyncio任务冲突）
# _field_enricher_instance: Optional[FieldEnricherService] = None


def get_field_enricher(
    max_concurrent: int = 2,
    max_retries: int = 3
) -> Optional[FieldEnricherService]:
    """
    创建字段增强服务实例

    注意：在Celery solo pool模式下，每次调用都会创建新实例。
    这是有意为之，避免多个并发任务共享同一个asyncio.Semaphore导致的任务冲突错误：
    "RuntimeError: Leaving task does not match the current task"

    Args:
        max_concurrent: 最大并发数
        max_retries: 最大重试次数

    Returns:
        字段增强服务实例（每次调用都是新实例）
    """
    enabled = os.getenv("COLLECTOR_FIELD_ENRICHER_ENABLED", "1").strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        logger.info("FieldEnricher disabled by COLLECTOR_FIELD_ENRICHER_ENABLED")
        return None

    max_retries = int(os.getenv("COLLECTOR_FIELD_ENRICHER_RETRIES", str(max_retries)))
    timeout = int(os.getenv("COLLECTOR_FIELD_ENRICHER_TIMEOUT", "12"))

    # 每次调用创建新实例，避免solo pool模式下的Semaphore冲突
    instance = FieldEnricherService(
        max_concurrent=max_concurrent,
        max_retries=max_retries,
        timeout=timeout
    )
    logger.debug(f"【FieldEnricher】创建新实例: 并发={max_concurrent}, 重试={max_retries}, 超时={timeout}s")
    return instance
