# -*- coding: utf-8 -*-

"""
Global Configuration Manager (Singleton)
Unified access point for config and prompts
"""

import os
import threading
import logging
from typing import Any, Dict, Optional

from .config_manager import ConfigManager
from .prompt_manager import PromptManager

logger = logging.getLogger(__name__)


class GlobalConfig:
    """
    全局配置管理器（单例模式）
    提供配置和提示词的统一访问接口
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
        """初始化全局配置管理器"""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._config_manager: Optional[ConfigManager] = None
                    self._prompt_manager: Optional[PromptManager] = None
                    self._config_path: Optional[str] = None
                    self._prompt_path: Optional[str] = None
                    GlobalConfig._initialized = True

    @classmethod
    def get_instance(cls) -> 'GlobalConfig':
        """获取全局配置管理器实例"""
        return cls()

    @classmethod
    def reset(cls):
        """重置单例实例（主要用于测试）"""
        with cls._lock:
            cls._instance = None
            cls._initialized = False

    def initialize(self, config_path: str = "config/config.yaml") -> bool:
        """
        初始化配置和提示词管理器

        Args:
            config_path: 配置文件路径

        Returns:
            是否初始化成功
        """
        success = True

        # 初始化配置管理器
        if self._config_manager is None:
            self._config_manager = ConfigManager()
            config_loaded = self._config_manager.load_config(config_path)
            if config_loaded:
                self._config_path = self._config_manager.get_config_path()
                logger.info(f"Config loaded from: {self._config_path}")
            else:
                logger.error("Failed to load configuration")
                success = False

        # 初始化提示词管理器
        if self._prompt_manager is None:
            if not self._init_prompt_manager():
                success = False

        return success

    def _init_prompt_manager(self) -> bool:
        """初始化提示词管理器"""
        if not self._config_manager:
            logger.warning("Config manager not initialized, cannot load prompts")
            return False

        config = self._config_manager.get_config()
        if not config:
            logger.warning("No configuration available for prompts")
            return False

        # 从配置中获取提示词配置
        prompts_config = config.get("prompts", {})
        language = prompts_config.get("language", "zh")
        prompts_filename = prompts_config.get("file", f"prompts_{language}.yaml")

        # 构建提示词文件的绝对路径
        base_dir = os.path.dirname(self._config_path)
        absolute_prompts_path = os.path.join(base_dir, prompts_filename)

        if not os.path.exists(absolute_prompts_path):
            logger.warning(f"Prompt file not found: {absolute_prompts_path}")
            return False

        try:
            self._prompt_manager = PromptManager(absolute_prompts_path)
            self._prompt_path = absolute_prompts_path
            logger.info(f"Prompts loaded from: {self._prompt_path} (language: {language})")
            return True
        except Exception as e:
            logger.error(f"Failed to load prompts: {e}")
            return False

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._config_manager is not None

    @property
    def prompt_manager(self) -> Optional[PromptManager]:
        """获取PromptManager实例"""
        return self._prompt_manager

    def get_config(self, path: Optional[str] = None, default: Any = None) -> Optional[Any]:
        """
        获取配置

        Args:
            path: 配置路径，如 "llm.chat.model"
            default: 默认值，当配置不存在时返回

        Returns:
            配置值
        """
        if not self._config_manager:
            logger.warning("Config manager not initialized")
            return default

        result = self._config_manager.get_config(path)
        return result if result is not None else default

    def get_prompt(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取提示词

        Args:
            name: 提示词名称
            default: 默认值

        Returns:
            提示词内容
        """
        if not self._prompt_manager:
            logger.warning("Prompt manager not initialized")
            return default

        return self._prompt_manager.get_prompt(name, default)

    def get_prompt_group(self, name: str) -> Dict[str, Any]:
        """
        获取提示词组

        Args:
            name: 提示词组名称

        Returns:
            提示词组字典
        """
        if not self._prompt_manager:
            logger.warning("Prompt manager not initialized")
            return {}

        return self._prompt_manager.get_prompt_group(name)

    def format_prompt(self, name: str, **kwargs) -> Optional[str]:
        """格式化提示词"""
        if not self._prompt_manager:
            logger.warning("Prompt manager not initialized")
            return None

        return self._prompt_manager.format_prompt(name, **kwargs)


# 全局便捷函数
def get_config(path: Optional[str] = None, default: Any = None) -> Optional[Any]:
    """便捷函数：获取配置值"""
    return GlobalConfig.get_instance().get_config(path, default)


def get_prompt(name: str, default: Optional[str] = None) -> Optional[str]:
    """便捷函数：获取提示词"""
    return GlobalConfig.get_instance().get_prompt(name, default)


def get_prompt_group(name: str) -> Dict[str, Any]:
    """便捷函数：获取提示词组"""
    return GlobalConfig.get_instance().get_prompt_group(name)


def format_prompt(name: str, **kwargs) -> Optional[str]:
    """便捷函数：格式化提示词"""
    return GlobalConfig.get_instance().format_prompt(name, **kwargs)
