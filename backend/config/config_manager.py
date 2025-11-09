# -*- coding: utf-8 -*-

"""
Configuration Manager
Loads and manages YAML-based configuration with environment variable substitution
"""

import os
import re
import yaml
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器 - 负责加载和管理系统配置"""

    def __init__(self):
        """初始化配置管理器"""
        self._config: Optional[Dict[str, Any]] = None
        self._config_path: Optional[str] = None
        self._env_vars: Dict[str, str] = {}

    def load_config(self, config_path: Optional[str] = None) -> bool:
        """
        加载配置文件

        Args:
            config_path: 配置文件路径，默认为 config/config.yaml

        Returns:
            是否成功加载
        """
        if not config_path:
            config_path = "config/config.yaml"

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            # 先保存配置路径，以便_load_env_vars()使用
            self._config_path = config_path

            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)

            # 加载环境变量并替换
            self._load_env_vars()
            config_data = self._replace_env_vars(config_data)

            self._config = config_data
            logger.info(f"Configuration loaded successfully: {self._config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return False

    def _load_env_vars(self) -> None:
        """
        加载环境变量

        优先级：
        1. 从配置文件所在目录的父目录查找.env（项目根目录）
        2. 从当前工作目录查找.env
        3. 使用系统环境变量
        """
        env_file_found = None

        # 策略1：尝试从配置文件路径向上查找项目根目录的.env
        if self._config_path:
            config_dir = os.path.dirname(os.path.abspath(self._config_path))
            project_root = os.path.dirname(config_dir)
            project_env = os.path.join(project_root, ".env")
            if os.path.exists(project_env):
                env_file_found = project_env

        # 策略2：尝试当前工作目录的.env
        if not env_file_found:
            cwd_env = ".env"
            if os.path.exists(cwd_env):
                env_file_found = os.path.abspath(cwd_env)

        # 加载找到的.env文件
        if env_file_found:
            try:
                with open(env_file_found, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            self._env_vars[key] = value
                            os.environ[key] = value
                logger.info(f"Loaded environment variables from {env_file_found}")
            except Exception as e:
                logger.warning(f"Failed to load .env file: {e}")
        else:
            logger.warning("No .env file found")

        # 策略3：加载系统环境变量（优先级最高，可覆盖.env）
        for key, value in os.environ.items():
            self._env_vars[key] = value

    def _replace_env_vars(self, config_data: Any) -> Any:
        """
        替换配置中的环境变量引用

        支持格式:
        - ${VAR}: 简单变量替换
        - ${VAR:default}: 变量不存在时使用默认值
        """
        if isinstance(config_data, dict):
            return {k: self._replace_env_vars(v) for k, v in config_data.items()}
        elif isinstance(config_data, list):
            return [self._replace_env_vars(item) for item in config_data]
        elif isinstance(config_data, str):
            # 匹配格式: ${VAR} 或 ${VAR:default}
            pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'

            def replace_match(match):
                var_name = match.group(1)
                default_value = match.group(2) if match.group(2) is not None else ""
                env_value = self._env_vars.get(var_name)
                return env_value if env_value is not None else default_value

            return re.sub(pattern, replace_match, config_data)
        else:
            return config_data

    def get_config(self, path: Optional[str] = None) -> Optional[Any]:
        """
        获取配置

        Args:
            path: 配置路径，如 "llm.chat.model"，为空则返回全部配置

        Returns:
            配置值
        """
        if self._config is None:
            return None

        if not path:
            return self._config

        # 通过路径获取配置
        keys = path.split('.')
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                logger.debug(f"Config path '{path}' not found")
                return None

        return value

    def get_config_path(self) -> Optional[str]:
        """获取配置文件路径"""
        return self._config_path

    def save_config(self, config_path: Optional[str] = None) -> bool:
        """
        保存配置

        Args:
            config_path: 保存路径，为空则保存到原路径

        Returns:
            是否保存成功
        """
        if self._config is None:
            logger.error("Configuration not loaded, cannot save")
            return False

        if config_path is None:
            if self._config_path is None:
                logger.error("Config path not specified")
                return False
            config_path = self._config_path

        try:
            # 创建目录
            dir_name = os.path.dirname(config_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)

            # 保存配置
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

            logger.info(f"Configuration saved: {config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config = config

    def deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度合并两个字典

        Args:
            base: 基础配置
            override: 覆盖配置

        Returns:
            合并后的配置
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.deep_merge(result[key], value)
            else:
                result[key] = value

        return result
