# -*- coding: utf-8 -*-

"""
LLM module
Provides LLM client interfaces for chat, embedding, and translation
"""

from .llm_client import LLMClient, LLMType
from .global_llm_manager import GlobalLLMManager, get_chat_client, get_fast_client, get_embedding_client
from .translator import Translator, get_translator
from .token_metrics import TokenMetrics, get_token_metrics

# 兼容性别名
def get_llm_client():
    """获取Chat客户端（别名）"""
    return get_chat_client()

__all__ = [
    'LLMClient',
    'LLMType',
    'GlobalLLMManager',
    'get_chat_client',
    'get_fast_client',
    'get_embedding_client',
    'get_llm_client',
    'Translator',
    'get_translator',
    'TokenMetrics',
    'get_token_metrics'
]
