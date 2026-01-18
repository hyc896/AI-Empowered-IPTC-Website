"""
配置加载器

本模块提供配置文件加载和环境变量替换功能。
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigLoader:
    """配置加载器"""

    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        """加载配置文件

        Args:
            config_path: 配置文件路径

        Returns:
            Dict[str, Any]: 配置字典

        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML解析错误
        """
        config_file = Path(config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 替换环境变量
            config = ConfigLoader._replace_env_vars(config)

            logger.info(f"配置文件加载成功: {config_path}")
            return config

        except yaml.YAMLError as e:
            logger.error(f"YAML解析错误: {e}")
            raise

    @staticmethod
    def _replace_env_vars(config: Any) -> Any:
        """递归替换配置中的环境变量

        支持格式: ${ENV_VAR} 或 ${ENV_VAR:default_value}

        Args:
            config: 配置对象（字典、列表或字符串）

        Returns:
            替换后的配置对象
        """
        if isinstance(config, dict):
            return {k: ConfigLoader._replace_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [ConfigLoader._replace_env_vars(item) for item in config]
        elif isinstance(config, str):
            return ConfigLoader._replace_env_var_string(config)
        else:
            return config

    @staticmethod
    def _replace_env_var_string(value: str) -> str:
        """替换字符串中的环境变量

        Args:
            value: 原始字符串

        Returns:
            替换后的字符串
        """
        import re

        # 匹配 ${VAR} 或 ${VAR:default}
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'

        def replacer(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else ""
            return os.environ.get(var_name, default_value)

        return re.sub(pattern, replacer, value)

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """验证配置完整性

        Args:
            config: 配置字典

        Returns:
            bool: 是否有效
        """
        required_keys = ['neo4j', 'llm']

        for key in required_keys:
            if key not in config:
                logger.error(f"配置缺少必需字段: {key}")
                return False

        # 验证Neo4j配置
        neo4j_config = config.get('neo4j', {})
        if not neo4j_config.get('password'):
            logger.error("Neo4j密码未配置")
            return False

        # 验证LLM配置
        llm_config = config.get('llm', {})
        if llm_config.get('provider') != 'custom' and not llm_config.get('api_key'):
            logger.error("LLM API密钥未配置")
            return False

        return True
