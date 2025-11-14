# -*- coding: utf-8 -*-

"""消息源模块注册中心"""

from .arxiv import validate_config as validate_arxiv_config

CONFIG_VALIDATORS = {
    'ArxivAdapter': validate_arxiv_config,
}


def validate_source_config(adapter_name: str, config: dict) -> tuple[bool, str]:
    """统一的配置验证入口

    Args:
        adapter_name: 适配器名称
        config: 配置字典

    Returns:
        (是否有效, 错误信息)
    """
    validator = CONFIG_VALIDATORS.get(adapter_name)
    if validator:
        return validator(config)
    return True, ""
