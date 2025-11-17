# -*- coding: utf-8 -*-

"""
LLM Translator
统一翻译服务，支持外文→中文翻译

功能特性：
- 并发控制（防止API过载）
- 自动重试机制（指数退避）
- 降级策略（翻译失败时返回截断原文）
- 批量翻译优化
"""

import asyncio
import logging
from typing import Optional, List

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

    def _get_llm_client(self):
        """延迟加载Fast LLM客户端"""
        if self._llm_client is None:
            from backend.llm import get_fast_client
            self._llm_client = get_fast_client()

            if self._llm_client is None:
                logger.error("【Translator】Fast LLM客户端未初始化")
                raise RuntimeError("Fast LLM client not initialized")

        return self._llm_client

    def _build_messages(self, text: str, context: Optional[str] = None) -> List[dict]:
        """
        构建翻译消息（system/user结构）

        Args:
            text: 待翻译文本
            context: 上下文信息（如"学术论文摘要"、"新闻报道"）

        Returns:
            消息列表
        """
        # System消息：定义角色和翻译规则
        system_content = "你是专业翻译助手，擅长将外文翻译成中文。翻译要求：准确完整、术语专业、语句流畅、不添加解释或评论。"

        if context:
            system_content += f"当前翻译内容类型：{context}。"

        # User消息：直接提供待翻译文本
        user_content = f"请将以下文本翻译成中文：\n\n{text}"

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
        max_tokens: int = 50000
    ) -> str:
        """
        翻译单个文本（异步）

        Args:
            text: 待翻译文本
            context: 上下文信息（可选，如"学术论文摘要"）
            max_tokens: 最大生成token数

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

                    # 构建system/user消息
                    messages = self._build_messages(text, context)

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

        # 创建翻译任务
        tasks = [self.translate(text, context) for text in texts]

        # 并发执行（Semaphore自动控制并发数）
        if show_progress:
            results = []
            for i, task in enumerate(asyncio.as_completed(tasks), 1):
                result = await task
                results.append(result)
                if i % 10 == 0 or i == len(texts):
                    logger.info(f"【Translator】批量翻译进度: {i}/{len(texts)}")
            return results
        else:
            return await asyncio.gather(*tasks)

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


# 全局单例
_translator_instance: Optional[Translator] = None


def get_translator(
    max_concurrent: int = 2,
    max_retries: int = 3
) -> Translator:
    """
    获取全局翻译器实例（单例模式）

    Args:
        max_concurrent: 最大并发翻译数
        max_retries: 最大重试次数

    Returns:
        全局翻译器实例
    """
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = Translator(
            max_concurrent=max_concurrent,
            max_retries=max_retries
        )
        logger.info(f"【Translator】翻译器初始化: 并发={max_concurrent}, 重试={max_retries}")
    return _translator_instance
