# -*- coding: utf-8 -*-

"""
LLM Translator
统一翻译服务，支持外文→中文翻译

功能特性：
- 并发控制（防止API过载）
- 自动重试机制（指数退避）
- 降级策略（翻译失败时返回截断原文）
- 批量翻译优化
- 网络错误优雅降级（不刷屏）
"""

import asyncio
import logging
from typing import Optional, List

# 网络错误类型（用于优雅降级）
try:
    from openai import APIConnectionError
    import httpx
    NETWORK_ERRORS = (APIConnectionError, httpx.ConnectError, httpx.TimeoutException, ConnectionError, OSError)
except ImportError:
    NETWORK_ERRORS = (ConnectionError, OSError)

logger = logging.getLogger(__name__)


class Translator:
    """
    LLM翻译器

    使用Fast LLM模型进行外文→中文翻译
    """

    def __init__(
        self,
        max_concurrent: int = 2,
        max_retries: int = 3,
        timeout: int = 30,
        fallback_truncate_length: int = 500
    ):
        """
        初始化翻译器

        Args:
            max_concurrent: 最大并发翻译数（默认2）
            max_retries: 最大重试次数（默认3）
            timeout: 单次翻译超时时间（秒，默认30）
            fallback_truncate_length: 降级时截断长度（默认500）
        """
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.timeout = timeout
        self.fallback_truncate_length = fallback_truncate_length

        # 并发控制信号量
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # 延迟加载LLM客户端（避免循环导入）
        self._llm_client = None

        # 网络错误日志标记（避免重复刷屏）
        self._network_error_logged = False

    def _get_llm_client(self):
        """延迟加载Fast LLM客户端"""
        if self._llm_client is None:
            from backend.llm import get_fast_client
            self._llm_client = get_fast_client()

            if self._llm_client is None:
                logger.error("【Translator】Fast LLM客户端未初始化")
                raise RuntimeError("Fast LLM client not initialized")

        return self._llm_client

    def _is_network_error(self, error: Exception) -> bool:
        """
        检测是否为网络连接错误

        Args:
            error: 异常对象

        Returns:
            是否为网络错误
        """
        # 直接类型检测
        if isinstance(error, NETWORK_ERRORS):
            return True

        # 字符串特征检测（兜底）
        error_str = str(error).lower()
        network_keywords = [
            "connection error",
            "connect error",
            "timeout",
            "timed out",
            "network",
            "unreachable",
            "connection refused",
            "no route to host"
        ]
        return any(keyword in error_str for keyword in network_keywords)

    def _handle_network_error(self) -> None:
        """
        处理网络错误（仅记录一次警告，避免刷屏）
        """
        if not self._network_error_logged:
            logger.warning("【Translator】网络连接失败，翻译跳过（检查VPN/代理）")
            self._network_error_logged = True

    # 语言代码到中文名称的映射
    LANG_NAMES = {
        'en': '英语', 'es': '西班牙语', 'fr': '法语', 'de': '德语',
        'ja': '日语', 'ko': '韩语', 'ru': '俄语', 'ar': '阿拉伯语',
        'pt': '葡萄牙语', 'it': '意大利语', 'zh': '中文'
    }

    def _build_messages(
        self,
        text: str,
        context: Optional[str] = None,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None
    ) -> List[dict]:
        """
        构建翻译消息（system/user结构）

        Args:
            text: 待翻译文本
            context: 上下文信息（如"学术论文摘要"、"新闻报道"）
            source_lang: 源语言代码（如"es"、"en"）
            target_lang: 目标语言代码（默认"zh"）

        Returns:
            消息列表
        """
        # 解析目标语言（默认中文）
        target = target_lang or 'zh'
        target_name = self.LANG_NAMES.get(target, '中文')

        # 解析源语言
        source_name = self.LANG_NAMES.get(source_lang) if source_lang else None

        # System消息：定义角色和翻译规则
        if source_name:
            system_content = f"你是专业翻译助手，擅长将{source_name}翻译成{target_name}。翻译要求：准确完整、术语专业、语句流畅、不添加解释或评论。"
        else:
            system_content = f"你是专业翻译助手，擅长将外文翻译成{target_name}。翻译要求：准确完整、术语专业、语句流畅、不添加解释或评论。"

        if context:
            system_content += f"当前翻译内容类型：{context}。"

        # User消息：直接提供待翻译文本
        user_content = f"请将以下文本翻译成{target_name}：\n\n{text}"

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]

    def _is_hallucination(self, translation: str) -> bool:
        """
        检测LLM幻觉输出

        Args:
            translation: 翻译结果

        Returns:
            是否为幻觉输出
        """
        # 简单文本模式检测
        simple_patterns = [
            "请提供您需要翻译的",
            "请提供需要翻译的",
            "我将为您翻译",
            "我会为您翻译",
            "以下是翻译结果",
            "翻译如下",
            "原文：",
            "中文翻译：",
            "Translation:",
            "Here is the translation"
        ]

        for pattern in simple_patterns:
            if pattern in translation:
                logger.warning(f"【Translator】检测到幻觉输出，包含模式: {pattern}")
                return True

        # 模板占位符检测（排除LaTeX数学公式）
        # 检测{{variable}}或{{abstract}}这种明显的模板占位符
        import re

        # 匹配模板占位符模式：{{单词}}
        template_pattern = r'\{\{[a-zA-Z_][a-zA-Z0-9_]*\}\}'
        if re.search(template_pattern, translation):
            logger.warning(f"【Translator】检测到幻觉输出，包含模板占位符: {{{{variable}}}}")
            return True

        return False

    async def translate(
        self,
        text: str,
        context: Optional[str] = None,
        max_tokens: int = 50000,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        翻译单个文本（异步）

        Args:
            text: 待翻译文本
            context: 上下文信息（可选，如"学术论文摘要"）
            max_tokens: 最大生成token数
            source_lang: 源语言（可选，如"es"、"en"，用于优化翻译提示）
            target_lang: 目标语言（可选，默认"zh"中文）
            **kwargs: 忽略其他未知参数（向后兼容）

        Returns:
            翻译后的中文文本，失败时返回截断的原文
        """
        if not text or not text.strip():
            return text

        async with self._semaphore:
            # 重试机制：最多max_retries次，指数退避
            for attempt in range(self.max_retries):
                try:
                    logger.debug(
                        f"【Translator】开始翻译 "
                        f"(尝试{attempt + 1}/{self.max_retries}, "
                        f"文本长度: {len(text)}, "
                        f"当前并发: {self.max_concurrent - self._semaphore._value}/{self.max_concurrent})"
                    )

                    start_time = asyncio.get_event_loop().time()

                    # 构建system/user消息（传递语言参数以优化提示）
                    messages = self._build_messages(text, context, source_lang, target_lang)

                    # 调用Fast LLM
                    llm_client = self._get_llm_client()
                    response = await llm_client.generate_with_messages_async(
                        messages=messages,
                        max_tokens=max_tokens,
                        source="Translator"
                    )

                    elapsed = asyncio.get_event_loop().time() - start_time
                    translation = response.choices[0].message.content.strip()

                    # 幻觉检测：如果检测到幻觉输出，触发降级
                    if self._is_hallucination(translation):
                        logger.warning(f"【Translator】检测到幻觉输出，触发降级策略")
                        return self._fallback(text)

                    logger.debug(f"【Translator】翻译完成 - 耗时: {elapsed:.1f}秒")

                    return translation

                except Exception as e:
                    # 优先检测网络错误（直接降级，不重试，不刷屏）
                    if self._is_network_error(e):
                        self._handle_network_error()
                        return self._fallback(text)

                    if attempt < self.max_retries - 1:
                        # 指数退避：1秒、2秒、4秒
                        retry_delay = 2 ** attempt
                        logger.warning(
                            f"【Translator】翻译失败 "
                            f"(尝试{attempt + 1}/{self.max_retries}): {e}，"
                            f"{retry_delay}秒后重试..."
                        )
                        await asyncio.sleep(retry_delay)
                    else:
                        # 所有重试失败，使用降级策略
                        logger.error(f"【Translator】翻译所有重试均失败: {e}")
                        return self._fallback(text)

    def _fallback(self, text: str) -> str:
        """
        降级策略：返回截断的原文

        Args:
            text: 原文

        Returns:
            截断后的文本 + 提示
        """
        if len(text) <= self.fallback_truncate_length:
            return text + "[AI翻译暂不可用]"
        else:
            return text[:self.fallback_truncate_length] + "...[AI翻译暂不可用]"

    async def translate_batch(
        self,
        texts: List[str],
        context: Optional[str] = None,
        show_progress: bool = False
    ) -> List[str]:
        """
        批量翻译（异步，自动并发控制）

        Args:
            texts: 文本列表
            context: 上下文信息
            show_progress: 是否显示进度日志

        Returns:
            翻译结果列表（与输入顺序对应）
        """
        if not texts:
            return []

        logger.info(f"【Translator】开始批量翻译: {len(texts)}条文本")

        # 串行执行（避免solo pool模式下的任务上下文冲突）
        # 注意：在Celery solo pool + nest_asyncio环境下，asyncio.gather/as_completed会导致任务上下文混乱
        results = []
        for i, text in enumerate(texts, 1):
            result = await self.translate(text, context)
            results.append(result)
            if show_progress and (i % 10 == 0 or i == len(texts)):
                logger.info(f"【Translator】批量翻译进度: {i}/{len(texts)}")

        return results

    def translate_sync(self, text: str, context: Optional[str] = None) -> str:
        """
        翻译单个文本（同步，阻塞）

        仅用于无法使用异步的场景（不推荐）

        Args:
            text: 待翻译文本
            context: 上下文信息

        Returns:
            翻译后的中文文本
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 如果没有事件循环，创建一个新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.translate(text, context))


# 全局单例（已废弃：在Celery solo pool模式下会导致asyncio任务冲突）
# _translator_instance: Optional[Translator] = None


def get_translator(
    max_concurrent: int = 2,
    max_retries: int = 3
) -> Translator:
    """
    创建翻译器实例

    注意：在Celery solo pool模式下，每次调用都会创建新实例。
    这是有意为之，避免多个并发任务共享同一个asyncio.Semaphore导致的任务冲突错误：
    "RuntimeError: Leaving task does not match the current task"

    Args:
        max_concurrent: 最大并发翻译数
        max_retries: 最大重试次数

    Returns:
        翻译器实例（每次调用都是新实例）
    """
    # 每次调用创建新实例，避免solo pool模式下的Semaphore冲突
    instance = Translator(
        max_concurrent=max_concurrent,
        max_retries=max_retries
    )
    logger.debug(f"【Translator】创建新实例: 并发={max_concurrent}, 重试={max_retries}")
    return instance
