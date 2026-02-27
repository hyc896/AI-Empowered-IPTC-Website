"""
Anthropic客户端实现

本模块实现Anthropic LLM客户端，支持Claude系列模型。
"""

from typing import List, Dict
import asyncio
import logging

try:
    from anthropic import Anthropic, AsyncAnthropic
except ImportError:
    Anthropic = None
    AsyncAnthropic = None

from .base import BaseLLMClient

logger = logging.getLogger(__name__)


class AnthropicClient(BaseLLMClient):
    """Anthropic客户端"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """初始化Anthropic客户端

        Args:
            api_key: Anthropic API密钥
            model: 模型名称（默认claude-3-5-sonnet-20241022）
        """
        if Anthropic is None:
            raise ImportError("请安装anthropic库: pip install anthropic")

        self.model = model
        self.client = Anthropic(api_key=api_key)
        self.async_client = AsyncAnthropic(api_key=api_key)

    async def generate_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """异步生成文本

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数

        Returns:
            str: 生成的文本
        """
        try:
            # 提取system消息
            system_message = None
            user_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)

            response = await self.async_client.messages.create(
                model=self.model,
                system=system_message,
                messages=user_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API调用失败: {e}")
            raise

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
        try:
            # 提取system消息
            system_message = None
            user_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)

            response = self.client.messages.create(
                model=self.model,
                system=system_message,
                messages=user_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API调用失败: {e}")
            raise
