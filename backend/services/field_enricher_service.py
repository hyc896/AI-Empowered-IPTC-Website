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
"""

import asyncio
import logging
from typing import Optional, List, Dict

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

        # 429错误追踪（TPM限流）
        self._consecutive_429_count = 0  # 连续429错误计数
        self._total_429_count = 0  # 总429错误计数
        self._backoff_seconds = 0  # 当前退避等待时间

    def _get_llm_client(self):
        """延迟加载Fast LLM客户端"""
        if self._llm_client is None:
            from backend.llm import get_fast_client
            self._llm_client = get_fast_client()

            if self._llm_client is None:
                logger.error("【FieldEnricher】Fast LLM客户端未初始化")
                raise RuntimeError("Fast LLM client not initialized")

        return self._llm_client

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
        处理429速率限制错误（指数退避）

        每次遇到429：
        - 连续计数+1
        - 退避时间翻倍（10秒 -> 20秒 -> 40秒 -> 80秒...）
        - 最长等待300秒（5分钟）
        """
        self._consecutive_429_count += 1
        self._total_429_count += 1

        # 指数退避：10秒 * 2^(连续次数-1)
        self._backoff_seconds = min(10 * (2 ** (self._consecutive_429_count - 1)), 300)

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
        content: str
    ) -> Dict[str, Optional[str]]:
        """
        增强字段（单条消息）

        并发调用地区分类、行业分类和AI标签分类，返回增强后的字段

        Args:
            title: 消息标题
            content: 消息内容

        Returns:
            字典包含：
            - region: 地区（如"中国/广东省/深圳市"）
            - industry_tags: 行业标签（如"人工智能,半导体"）
            - ai_tag: AI分类标签（"AI科研信息"/"AI产业信息"/"AI治理信息"）
            失败时对应字段为None
        """
        if not title or not content:
            logger.warning("【FieldEnricher】标题或内容为空，跳过增强")
            return {"region": None, "industry_tags": None, "ai_tag": None}

        # 并发执行地区分类、行业分类和AI标签分类
        region_task = self._classify_region(title, content)
        industry_task = self._classify_industry(title, content)
        ai_tag_task = self._classify_ai_tag(title, content)

        region, industry_tags, ai_tag = await asyncio.gather(region_task, industry_task, ai_tag_task)

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
        批量增强字段（异步，自动并发控制）

        Args:
            messages: 消息列表，每条包含title和content
            show_progress: 是否显示进度日志

        Returns:
            增强结果列表（与输入顺序对应）
        """
        if not messages:
            return []

        logger.info(f"【FieldEnricher】开始批量增强: {len(messages)}条消息")

        # 创建增强任务
        tasks = [
            self.enrich_fields(msg.get('title', ''), msg.get('content', ''))
            for msg in messages
        ]

        # 并发执行（Semaphore自动控制并发数）
        if show_progress:
            results = []
            for i, task in enumerate(asyncio.as_completed(tasks), 1):
                result = await task
                results.append(result)
                if i % 10 == 0 or i == len(messages):
                    logger.info(f"【FieldEnricher】批量增强进度: {i}/{len(messages)}")
            return results
        else:
            return await asyncio.gather(*tasks)

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
                    response = await llm_client.generate_with_messages_async(
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=100
                    )

                    region = response.choices[0].message.content.strip()

                    # 验证格式：不超过200字符，不包含非法字符
                    if region and len(region) < 200 and not self._is_invalid_region(region):
                        logger.debug(f"【FieldEnricher】地区分类成功: {region}")
                        self._reset_rate_limit_counter()  # 成功则重置429计数
                        return region
                    else:
                        logger.warning(f"【FieldEnricher】地区分类结果格式异常: {region}")
                        return None

                except Exception as e:
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
                    response = await llm_client.generate_with_messages_async(
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=150
                    )

                    tags = response.choices[0].message.content.strip()

                    # 验证格式：逗号分隔，最多3个标签
                    if tags:
                        tag_list = [t.strip() for t in tags.split(',')]
                        if len(tag_list) <= 3 and all(tag_list):
                            logger.debug(f"【FieldEnricher】行业分类成功: {tags}")
                            self._reset_rate_limit_counter()  # 成功则重置429计数
                            return tags
                        elif len(tag_list) > 3:
                            # 只保留前3个
                            tags = ','.join(tag_list[:3])
                            logger.warning(f"【FieldEnricher】行业标签超过3个，截取前3个: {tags}")
                            self._reset_rate_limit_counter()  # 成功则重置429计数
                            return tags
                        else:
                            logger.warning(f"【FieldEnricher】行业分类结果格式异常: {tags}")
                            return None
                    else:
                        logger.warning("【FieldEnricher】行业分类返回空结果")
                        return None

                except Exception as e:
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

        prompt = f"""请分析以下新闻内容，判断事件的**物理发生地**（而非涉及的参与方）。

核心原则：标注事件发生的地点，而不是事件涉及的实体或参与方。

判断规则：
1. 优先识别事件的**物理发生地点**：
   - 会议/会见/访问：标注举办城市（如"中国外交部长在北京会见欧盟代表" → "中国/北京市"）
   - 政策发布：标注发布机构所在地（如"深圳发布AI政策" → "中国/广东省/深圳市"）
   - 企业投资：标注投资目的地（如"某公司在美国建数据中心" → "美国"）
   - 突发事件：标注事件发生地（如"东京发生地震" → "日本/东京都"）

2. 仅在无法确定具体地点时考虑实体归属：
   - 组织决议：标注组织总部所在地或决议签署地，若无法确定则标注组织名（如"欧盟通过法案" → "欧盟"）
   - 全球市场：标注"全球"（如"国际油价上涨"、"黄金价格波动"）

3. 格式规范：
   - 国家级事件：返回国家名（中文）
   - 省级事件：返回"国家/省份"（用斜杠分隔）
   - 城市级事件：返回"国家/省份/城市"（用斜杠分隔）

4. 避免混淆事件主体和地点：
   - 错误示例："中国外长会见美国代表" → "中国/美国"（错！应该看会见地点）
   - 正确示例："中国外长在北京会见美国代表" → "中国/北京市"（对！）
   - 正确示例："美国总统访问日本" → "日本"（对！访问发生在日本）

示例：
- "现货黄金站上4170美元/盎司" → "全球"
- "Anthropic将在美国投资500亿美元建设数据中心" → "美国"
- "深圳发布AI产业支持政策" → "中国/广东省/深圳市"
- "外交部发言人在北京回应欧盟声明" → "中国/北京市"
- "中美元首在旧金山会晤" → "美国/加利福尼亚州/旧金山市"
- "欧盟委员会在布鲁塞尔通过AI监管法案" → "欧盟/比利时/布鲁塞尔"

新闻标题：{title}
新闻内容：{content_excerpt}

仅返回地区信息（如"中国/北京市"、"美国/加利福尼亚州"、"全球"），不要任何解释。"""

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

        prompt = f"""请为以下新闻打上行业标签（最多3个）。

可选行业标签（只能从以下列表选择）：
人工智能、半导体/芯片、计算机软件、通信设备、电子元器件、互联网服务、新能源/电动车、
生物医药、医疗器械、金融科技、汽车制造、机械设备、化工材料、钢铁有色、
能源采掘、电力公用、房地产建筑、交通运输、商贸零售、消费品、农林牧渔、
传媒娱乐、教育培训、金融服务、环保工程、航空航天、国防军工、其他行业

判断规则：
1. 只标注行业，不标注资产类型（股票、债券等）或事件类型（融资、并购等）
2. 优先选择最相关的1-2个核心行业
3. 如果新闻涉及AI相关内容（ChatGPT、大模型、机器学习、深度学习、神经网络等），必须包含"人工智能"标签
4. 如果无法明确判断行业，标注"其他行业"
5. 多个标签用英文逗号分隔

示例：
- "Anthropic将在美国投资500亿美元建设数据中心" → "人工智能"
- "英伟达发布新一代AI芯片" → "人工智能,半导体/芯片"
- "比亚迪发布新款电动车" → "新能源/电动车,汽车制造"
- "现货黄金站上4170美元/盎司" → "其他行业"

新闻标题：{title}
新闻内容：{content_excerpt}

仅返回行业标签（逗号分隔，如"人工智能,半导体/芯片"），不要任何解释。"""

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
                    response = await llm_client.generate_with_messages_async(
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=50
                    )

                    tag = response.choices[0].message.content.strip()

                    # 验证格式：必须是三个标签之一
                    valid_tags = ["AI科研信息", "AI产业信息", "AI治理信息"]
                    if tag in valid_tags:
                        logger.debug(f"【FieldEnricher】AI标签分类成功: {tag}")
                        self._reset_rate_limit_counter()
                        return tag
                    else:
                        logger.warning(f"【FieldEnricher】AI标签分类结果异常: {tag}")
                        return None

                except Exception as e:
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

        prompt = f"""请为以下新闻进行AI相关分类，从三个类别中选择一个。

可选类别（只能选择其中一个）：
1. AI治理信息 - AI相关的安全、法律、政策、监管、伦理、治理等内容
2. AI科研信息 - AI相关的学术研究、论文、技术突破、算法创新等内容
3. AI产业信息 - AI相关的产业动态、企业新闻、投资融资、产品发布、市场应用等内容

判断规则（按优先级）：
1. **优先判断是否属于AI治理信息**：
   - 关键词：政策、法律、法规、监管、治理、伦理、安全、隐私、合规、标准、规范
   - 示例："欧盟通过AI法案"、"AI安全监管政策"、"算法伦理规范" → AI治理信息

2. 如果不属于治理，判断是否属于科研信息：
   - 关键词：论文、研究、算法、模型、技术突破、学术成果、arXiv、会议发表
   - 示例："Nature发表AI新算法"、"清华发布大模型论文" → AI科研信息

3. 如果以上都不是，归类为产业信息：
   - 关键词：公司、企业、投资、融资、产品、发布、应用、市场、数据中心、芯片
   - 示例："Anthropic投资数据中心"、"英伟达发布AI芯片" → AI产业信息

特殊情况处理：
- 如果新闻同时涉及多个类别，优先选择AI治理信息
- 如果新闻与AI无关，返回"AI产业信息"（作为默认类别）

示例：
- "欧盟通过人工智能法案，加强AI监管" → "AI治理信息"
- "清华大学发表AI大模型最新研究论文" → "AI科研信息"
- "Anthropic将在美国投资500亿美元建设数据中心" → "AI产业信息"
- "英伟达发布新一代AI芯片" → "AI产业信息"
- "OpenAI发布安全对齐新标准" → "AI治理信息"

新闻标题：{title}
新闻内容：{content_excerpt}

仅返回分类结果（"AI科研信息"、"AI产业信息"或"AI治理信息"），不要任何解释。"""

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


# 全局单例
_field_enricher_instance: Optional[FieldEnricherService] = None


def get_field_enricher(
    max_concurrent: int = 2,
    max_retries: int = 3
) -> FieldEnricherService:
    """
    获取全局字段增强服务实例（单例模式）

    Args:
        max_concurrent: 最大并发数
        max_retries: 最大重试次数

    Returns:
        全局字段增强服务实例
    """
    global _field_enricher_instance
    if _field_enricher_instance is None:
        _field_enricher_instance = FieldEnricherService(
            max_concurrent=max_concurrent,
            max_retries=max_retries
        )
        logger.info(f"【FieldEnricher】字段增强服务初始化: 并发={max_concurrent}, 重试={max_retries}")
    return _field_enricher_instance
