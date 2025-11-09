# -*- coding: utf-8 -*-

"""
PersonalAgent LLM module
Provides LLM client interfaces for chat and embedding
"""

from .llm_client import LLMClient, LLMType
from .global_llm_manager import GlobalLLMManager, get_chat_client, get_fast_client, get_embedding_client

# 兼容性别名
def get_llm_client():
    """获取Chat客户端（别名）"""
    return get_chat_client()

__all__ = ['LLMClient', 'LLMType', 'GlobalLLMManager', 'get_chat_client', 'get_fast_client', 'get_embedding_client', 'get_llm_client']
