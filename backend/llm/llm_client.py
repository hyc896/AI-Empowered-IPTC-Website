# -*- coding: utf-8 -*-

"""
LLM Client
OpenAI-compatible LLM client for embedding and text generation
"""

from enum import Enum
from openai import OpenAI, APIError, AsyncOpenAI, APIConnectionError
from typing import List, Dict, Any, Optional
import logging
import httpx

logger = logging.getLogger(__name__)

# 延迟导入token_metrics（避免循环导入）
_token_metrics = None

def _get_token_metrics():
    """延迟加载token_metrics"""
    global _token_metrics
    if _token_metrics is None:
        from backend.llm.token_metrics import get_token_metrics
        _token_metrics = get_token_metrics()
    return _token_metrics


class LLMType(Enum):
    """LLM类型枚举"""
    CHAT = "chat"
    EMBEDDING = "embedding"


class LLMClient:
    """
    统一的LLM客户端，支持OpenAI兼容接口
    """

    def __init__(self, llm_type: LLMType, config: Dict[str, Any]):
        """
        初始化LLM客户端

        Args:
            llm_type: LLM类型（CHAT或EMBEDDING）
            config: 配置字典，包含：
                - model: 模型名称
                - api_key: API密钥
                - base_url: API基础URL
                - timeout: 超时时间（可选，默认60秒）
                - temperature: 温度参数（可选，默认0.7）
        """
        self.llm_type = llm_type
        self.config = config
        self.model = config.get("model")
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url")
        self.timeout = config.get("timeout", 60)

        if not self.api_key or not self.base_url or not self.model:
            raise ValueError("API key, base URL, and model must be provided")

        # 创建同步客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=0  # 禁用内部重试，由上层业务逻辑控制重试
        )

        # 创建异步客户端
        # 禁用max_retries：防止httpx内部重试机制与asyncio任务上下文冲突
        # 在Celery+asyncio环境中，httpx重试回调可能在错误的任务上下文执行
        # 导致RuntimeError: Leaving task does not match the current task
        # 重试逻辑由FieldEnricherService/Translator等上层服务自行控制
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=0  # 禁用内部重试，由上层业务逻辑控制重试
        )

    def generate(self, prompt: str, **kwargs) -> str:
        """
        简单的生成方法（单轮对话）

        Args:
            prompt: 用户输入
            **kwargs: 其他参数

        Returns:
            生成的文本
        """
        messages = [{"role": "user", "content": prompt}]
        return self.generate_with_messages(messages, **kwargs)

    def generate_with_messages(self, messages: List[Dict[str, Any]], source: Optional[str] = None, **kwargs):
        """
        使用消息列表生成响应（同步）

        Args:
            messages: 消息列表
            source: 调用来源（用于Token统计）
            **kwargs: 其他参数（temperature, tools等）

        Returns:
            OpenAI响应对象
        """
        if self.llm_type == LLMType.CHAT:
            return self._openai_chat_completion(messages, source=source, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM type for message generation: {self.llm_type}")

    async def generate_with_messages_async(self, messages: List[Dict[str, Any]], source: Optional[str] = None, **kwargs):
        """
        使用消息列表生成响应（异步）

        Args:
            messages: 消息列表
            source: 调用来源（用于Token统计）
            **kwargs: 其他参数

        Returns:
            OpenAI响应对象
        """
        if self.llm_type == LLMType.CHAT:
            return await self._openai_chat_completion_async(messages, source=source, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM type for message generation: {self.llm_type}")

    def generate_with_messages_stream(self, messages: List[Dict[str, Any]], **kwargs):
        """流式生成（同步）"""
        if self.llm_type == LLMType.CHAT:
            return self._openai_chat_completion_stream(messages, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM type for stream generation: {self.llm_type}")

    async def generate_with_messages_stream_async(self, messages: List[Dict[str, Any]], **kwargs):
        """流式生成（异步）"""
        if self.llm_type == LLMType.CHAT:
            async for chunk in self._openai_chat_completion_stream_async(messages, **kwargs):
                yield chunk
        else:
            raise ValueError(f"Unsupported LLM type for stream generation: {self.llm_type}")

    def generate_embedding(self, text: str, **kwargs) -> List[float]:
        """
        生成文本的向量表示

        Args:
            text: 输入文本
            **kwargs: 其他参数（output_dim等）

        Returns:
            向量列表
        """
        if self.llm_type == LLMType.EMBEDDING:
            return self._openai_embedding(text, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM type for embedding generation: {self.llm_type}")

    def _openai_chat_completion(self, messages: List[Dict[str, Any]], source: Optional[str] = None, **kwargs):
        """同步聊天完成"""
        try:
            temperature = kwargs.get("temperature", self.config.get("temperature", 0.7))
            tools = kwargs.get("tools", None)
            max_tokens = kwargs.get("max_tokens", None)

            create_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }

            # 添加max_tokens（如果提供）
            if max_tokens:
                create_params["max_tokens"] = max_tokens

            if tools:
                create_params["tools"] = tools
                create_params['tool_choice'] = "auto"

            response = self.client.chat.completions.create(**create_params)

            # 记录Token使用
            if hasattr(response, 'usage') and response.usage:
                token_metrics = _get_token_metrics()
                token_metrics.record(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    source=source or f"LLM:{self.model}"
                )

            return response
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def _openai_chat_completion_async(self, messages: List[Dict[str, Any]], source: Optional[str] = None, **kwargs):
        """异步聊天完成"""
        try:
            temperature = kwargs.get("temperature", self.config.get("temperature", 0.7))
            tools = kwargs.get("tools", None)
            max_tokens = kwargs.get("max_tokens", None)

            create_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }

            # 添加max_tokens（如果提供）
            if max_tokens:
                create_params["max_tokens"] = max_tokens

            if tools:
                create_params["tools"] = tools
                create_params['tool_choice'] = "auto"

            response = await self.async_client.chat.completions.create(**create_params)

            # 记录Token使用
            if hasattr(response, 'usage') and response.usage:
                token_metrics = _get_token_metrics()
                token_metrics.record(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    source=source or f"LLM:{self.model}"
                )

            return response
        except (APIConnectionError, httpx.ConnectError, httpx.TimeoutException) as e:
            # 网络连接错误：记录警告而非异常，避免刷屏
            logger.warning(f"【LLM】网络连接失败（检查VPN/代理）: {type(e).__name__}")
            raise
        except APIError as e:
            logger.error(f"【LLM】API错误: {e}")
            raise

    def _openai_chat_completion_stream(self, messages: List[Dict[str, Any]], **kwargs):
        """同步流式聊天完成"""
        try:
            temperature = kwargs.get("temperature", self.config.get("temperature", 0.7))
            tools = kwargs.get("tools", None)

            create_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
            }

            if tools:
                create_params["tools"] = tools
                create_params['tool_choice'] = "auto"

            stream = self.client.chat.completions.create(**create_params)
            return stream
        except APIError as e:
            logger.error(f"OpenAI API stream error: {e}")
            raise

    async def _openai_chat_completion_stream_async(self, messages: List[Dict[str, Any]], **kwargs):
        """异步流式聊天完成（异步生成器）"""
        try:
            temperature = kwargs.get("temperature", self.config.get("temperature", 0.7))
            tools = kwargs.get("tools", None)

            create_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
            }

            if tools:
                create_params["tools"] = tools
                create_params['tool_choice'] = "auto"

            stream = await self.async_client.chat.completions.create(**create_params)

            # 直接返回流对象，它已经是异步迭代器
            async for chunk in stream:
                yield chunk
        except APIError as e:
            logger.error(f"OpenAI API async stream error: {e}")
            raise

    def _openai_embedding(self, text: str, **kwargs) -> List[float]:
        """生成嵌入向量"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=[text]
            )
            embedding = response.data[0].embedding

            if hasattr(response, 'usage') and response.usage:
                logger.debug(f"Embedding token usage: {response.usage.total_tokens}")

            # 如果指定了输出维度，进行裁剪和归一化
            output_dim = kwargs.get("output_dim", self.config.get("output_dim", 0))
            if output_dim and len(embedding) > output_dim:
                import math
                embedding = embedding[:output_dim]
                norm = math.sqrt(sum(x**2 for x in embedding))
                if norm > 0:
                    embedding = [x / norm for x in embedding]

            return embedding
        except APIError as e:
            logger.error(f"OpenAI API error during embedding: {e}")
            raise
