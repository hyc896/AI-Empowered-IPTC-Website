# -*- coding: utf-8 -*-

"""
Prompt Manager
Manages YAML-based prompts for different modules
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PromptManager:
    """提示词管理器 - 从YAML文件加载和管理提示词"""

    def __init__(self, prompt_config_path: Optional[str] = None):
        """
        初始化提示词管理器

        Args:
            prompt_config_path: 提示词配置文件路径
        """
        self.prompts = {}

        if prompt_config_path and os.path.exists(prompt_config_path):
            try:
                with open(prompt_config_path, 'r', encoding='utf-8') as f:
                    self.prompts = yaml.safe_load(f) or {}
                logger.info(f"Prompts loaded from: {prompt_config_path}")
            except Exception as e:
                logger.error(f"Failed to load prompts: {e}")
                raise
        else:
            logger.warning(f"Prompt config file not found: {prompt_config_path}")
            raise FileNotFoundError(f"Prompt config file not found: {prompt_config_path}")

    def get_prompt(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取单个提示词

        Args:
            name: 提示词名称，支持点号分隔的路径，如 "chat.system"
            default: 默认值

        Returns:
            提示词内容
        """
        keys = name.split('.')
        value = self.prompts

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                logger.debug(f"Prompt '{name}' not found")
                return default

        return value if isinstance(value, str) else default

    def get_prompt_group(self, name: str) -> Dict[str, Any]:
        """
        获取提示词组

        Args:
            name: 提示词组名称，如 "chat.intent_analysis"

        Returns:
            提示词组字典
        """
        keys = name.split('.')
        value = self.prompts

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                logger.debug(f"Prompt group '{name}' not found")
                return {}

        return value if isinstance(value, dict) else {}

    def format_prompt(self, name: str, **kwargs) -> Optional[str]:
        """
        获取并格式化提示词

        Args:
            name: 提示词名称
            **kwargs: 格式化参数

        Returns:
            格式化后的提示词
        """
        template = self.get_prompt(name)
        if template is None:
            return None

        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing format key {e} for prompt '{name}'")
            return None
