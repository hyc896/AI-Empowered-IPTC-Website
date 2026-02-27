"""
LLM基类接口

本模块定义LLM客户端的统一接口，支持多种LLM提供商。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseLLMClient(ABC):
    """LLM客户端基类"""

    @abstractmethod
    async def generate_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """异步生成文本

        Args:
            messages: 消息列表，格式为 [{"role": "system", "content": "..."}, ...]
            temperature: 温度参数（0-1）
            max_tokens: 最大token数
            **kwargs: 其他参数

        Returns:
            str: 生成的文本
        """
        pass

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """同步生成文本

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数

        Returns:
            str: 生成的文本
        """
        pass
