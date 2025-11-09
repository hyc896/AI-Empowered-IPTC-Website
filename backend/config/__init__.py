# -*- coding: utf-8 -*-

"""
PersonalAgent Config module
Configuration and prompt management
"""

from .config_manager import ConfigManager
from .prompt_manager import PromptManager
from .global_config import GlobalConfig, get_config, get_prompt, get_prompt_group

def get_prompt_manager() -> PromptManager:
    """获取全局PromptManager实例"""
    return GlobalConfig.get_instance().prompt_manager

__all__ = [
    'ConfigManager',
    'PromptManager',
    'GlobalConfig',
    'get_config',
    'get_prompt',
    'get_prompt_group',
    'get_prompt_manager'
]
