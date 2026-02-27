"""
配置管理路由
处理LLM配置的获取和更新
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import yaml
from pathlib import Path

router = APIRouter(prefix="/config", tags=["config"])


class LLMConfig(BaseModel):
    """LLM配置模型"""
    provider: str
    model: str
    api_key: str
    base_url: str
    temperature: float
    max_tokens: int


class LLMConfigUpdate(BaseModel):
    """LLM配置更新模型（所有字段可选）"""
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


def get_config_path() -> Path:
    """获取配置文件路径"""
    return Path(__file__).parent.parent.parent.parent.parent / "GraphRAG" / "config" / "default_config.yaml"


@router.get("/llm", response_model=LLMConfig)
async def get_llm_config():
    """
    获取当前LLM配置

    Returns:
        当前的LLM配置信息
    """
    try:
        import os
        config_path = get_config_path()

        # 调试日志
        print(f"🔍 调试信息:")
        print(f"  __file__ = {Path(__file__)}")
        print(f"  当前工作目录 = {Path.cwd()}")
        print(f"  计算的配置文件路径 = {config_path}")
        print(f"  配置文件是否存在 = {config_path.exists()}")
        print(f"  配置文件绝对路径 = {config_path.absolute()}")

        if not config_path.exists():
            raise HTTPException(status_code=404, detail=f"配置文件不存在: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        llm_config = config.get('llm', {})

        # 处理API Key - 优先从环境变量读取
        api_key = llm_config.get('api_key', '')
        if isinstance(api_key, str) and api_key.startswith('${'):
            # 从环境变量读取
            env_var_name = api_key.split('${')[1].split('}')[0].split(':')[0]
            api_key = os.getenv(env_var_name, '')
            print(f"🔑 读取API Key: 环境变量名={env_var_name}, 值={'已设置' if api_key else '未设置'}")

        # 处理Base URL - 优先从环境变量读取，否则使用默认值
        base_url = llm_config.get('base_url', '')
        if isinstance(base_url, str) and base_url.startswith('${'):
            # 提取环境变量名和默认值
            parts = base_url.split('${')[1].rstrip('}').split(':')
            env_var_name = parts[0]
            default_value = parts[1] if len(parts) > 1 else ''
            base_url = os.getenv(env_var_name, default_value)

        return LLMConfig(
            provider=llm_config.get('provider', 'openai'),
            model=llm_config.get('model', 'qwen-plus'),
            api_key=api_key,
            base_url=base_url,
            temperature=llm_config.get('temperature', 0.3),
            max_tokens=llm_config.get('max_tokens', 4000)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.put("/llm")
async def update_llm_config(config_update: LLMConfigUpdate):
    """
    更新LLM配置

    Args:
        config_update: 要更新的配置项

    Returns:
        更新结果
    """
    try:
        config_path = get_config_path()

        if not config_path.exists():
            raise HTTPException(status_code=404, detail="配置文件不存在")

        # 读取现有配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 更新LLM配置
        if 'llm' not in config:
            config['llm'] = {}

        llm_config = config['llm']

        # 只更新提供的字段
        if config_update.provider is not None:
            llm_config['provider'] = config_update.provider
        if config_update.model is not None:
            llm_config['model'] = config_update.model
        if config_update.api_key is not None:
            llm_config['api_key'] = config_update.api_key
        if config_update.base_url is not None:
            llm_config['base_url'] = config_update.base_url
        if config_update.temperature is not None:
            llm_config['temperature'] = config_update.temperature
        if config_update.max_tokens is not None:
            llm_config['max_tokens'] = config_update.max_tokens

        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

        return {"message": "配置更新成功", "config": llm_config}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")
