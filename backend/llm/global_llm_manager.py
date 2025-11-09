# -*- coding: utf-8 -*-

"""
Global LLM Manager (Singleton)
Provides global access to chat and embedding LLM clients
"""

from typing import Optional
import threading
import logging
import json
import asyncio

from .llm_client import LLMClient, LLMType

logger = logging.getLogger(__name__)


class GlobalLLMManager:
    """
    全局LLM管理器（单例模式）
    管理chat和embedding两个客户端实例
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """确保单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化管理器"""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._chat_client: Optional[LLMClient] = None
                    self._fast_client: Optional[LLMClient] = None  # 快速模型客户端
                    self._embedding_client: Optional[LLMClient] = None
                    self._tools_registry = {}  # 工具注册表
                    GlobalLLMManager._initialized = True

    @classmethod
    def get_instance(cls) -> 'GlobalLLMManager':
        """获取全局LLM管理器实例"""
        return cls()

    @classmethod
    def reset(cls):
        """重置单例实例（主要用于测试）"""
        with cls._lock:
            cls._instance = None
            cls._initialized = False

    def initialize(self, chat_config: dict, embedding_config: dict, fast_config: dict = None):
        """
        初始化LLM客户端

        Args:
            chat_config: Chat模型配置（主模型）
            embedding_config: Embedding模型配置
            fast_config: Fast模型配置（可选，用于简单任务）
        """
        with self._lock:
            try:
                # 初始化Chat客户端（主模型）
                if chat_config:
                    self._chat_client = LLMClient(
                        llm_type=LLMType.CHAT,
                        config=chat_config
                    )
                    logger.info(f"Chat client initialized with model: {chat_config.get('model')}")

                # 初始化Fast客户端（快速模型）
                if fast_config:
                    self._fast_client = LLMClient(
                        llm_type=LLMType.CHAT,
                        config=fast_config
                    )
                    logger.info(f"Fast client initialized with model: {fast_config.get('model')}")

                # 初始化Embedding客户端
                if embedding_config:
                    self._embedding_client = LLMClient(
                        llm_type=LLMType.EMBEDDING,
                        config=embedding_config
                    )
                    logger.info(f"Embedding client initialized with model: {embedding_config.get('model')}")

                logger.info("GlobalLLMManager initialized successfully")
            except Exception as e:
                logger.error(f"GlobalLLMManager initialization failed: {e}")
                raise

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._chat_client is not None or self._embedding_client is not None

    @property
    def chat_client(self) -> Optional[LLMClient]:
        """获取Chat客户端（主模型）"""
        if self._chat_client is None:
            logger.warning("Chat client not initialized")
        return self._chat_client

    @property
    def fast_client(self) -> Optional[LLMClient]:
        """获取Fast客户端（快速模型）"""
        if self._fast_client is None:
            logger.warning("Fast client not initialized")
        return self._fast_client

    @property
    def embedding_client(self) -> Optional[LLMClient]:
        """获取Embedding客户端"""
        if self._embedding_client is None:
            logger.warning("Embedding client not initialized")
        return self._embedding_client

    def register_tool(self, tool_name: str, tool_func):
        """
        注册工具函数

        Args:
            tool_name: 工具名称
            tool_func: 工具函数（可以是同步或异步）
        """
        self._tools_registry[tool_name] = tool_func
        logger.info(f"Tool registered: {tool_name}")

    def get_tool(self, tool_name: str):
        """获取已注册的工具"""
        return self._tools_registry.get(tool_name)

    async def execute_tool(self, tool_name: str, tool_args: dict):
        """
        执行工具调用

        Args:
            tool_name: 工具名称
            tool_args: 工具参数

        Returns:
            工具执行结果
        """
        tool_func = self.get_tool(tool_name)
        if tool_func is None:
            error_msg = f"Tool not found: {tool_name}"
            logger.error(error_msg)
            return {"error": error_msg}

        try:
            # 判断是否为异步函数
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**tool_args)
            else:
                result = tool_func(**tool_args)

            logger.info(f"Tool {tool_name} executed successfully")
            return result
        except Exception as e:
            logger.exception(f"Tool {tool_name} execution failed: {e}")
            return {"error": str(e)}

    async def chat_with_tools(
        self,
        messages: list,
        tools: list = None,
        max_iterations: int = 5,
        **kwargs
    ) -> str:
        """
        带工具调用的对话（自动执行工具并循环）

        Args:
            messages: 消息列表
            tools: 可用工具的定义列表
            max_iterations: 最大工具调用轮次
            **kwargs: 其他参数

        Returns:
            最终的回复文本
        """
        if self._chat_client is None:
            raise RuntimeError("Chat client not initialized")

        iteration = 0
        while iteration < max_iterations:
            iteration += 1

            # 调用LLM
            response = await self._chat_client.generate_with_messages_async(
                messages,
                tools=tools,
                **kwargs
            )

            message = response.choices[0].message

            # 如果没有工具调用，直接返回
            if not message.tool_calls:
                return message.content

            # 添加LLM的响应到消息历史
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in message.tool_calls
                ]
            })

            # 并行执行所有工具调用
            tool_results = []
            for tc in message.tool_calls:
                function_name = tc.function.name
                try:
                    function_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    function_args = {}

                result = await self.execute_tool(function_name, function_args)
                tool_results.append({
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(result, ensure_ascii=False),
                    "tool_call_id": tc.id
                })

            # 添加工具结果到消息历史
            messages.extend(tool_results)

        # 达到最大轮次，强制返回最后一次响应
        logger.warning(f"Reached max tool call iterations ({max_iterations})")
        return message.content if message.content else "工具调用次数过多，请重新提问"


# 全局便捷函数
def get_chat_client() -> Optional[LLMClient]:
    """获取全局Chat客户端（主模型）"""
    return GlobalLLMManager.get_instance().chat_client


def get_fast_client() -> Optional[LLMClient]:
    """获取全局Fast客户端（快速模型）"""
    return GlobalLLMManager.get_instance().fast_client


def get_embedding_client() -> Optional[LLMClient]:
    """获取全局Embedding客户端"""
    return GlobalLLMManager.get_instance().embedding_client


def initialize_llm(chat_config: dict, embedding_config: dict, fast_config: dict = None):
    """初始化全局LLM管理器"""
    GlobalLLMManager.get_instance().initialize(chat_config, embedding_config, fast_config)
