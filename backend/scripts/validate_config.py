# -*- coding: utf-8 -*-

"""
配置校验工具
对比.env和config.yaml，报告实际生效的配置值

Usage:
    python backend/scripts/validate_config.py
"""

import os
import sys
import yaml
from pathlib import Path

# Windows控制台UTF-8编码支持
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def load_env_file(env_path: str) -> dict:
    """加载.env文件"""
    env_vars = {}
    if not os.path.exists(env_path):
        return env_vars

    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip().strip('"').strip("'")

    return env_vars


def extract_env_placeholders(config_data: dict, prefix: str = "") -> dict:
    """递归提取config.yaml中的环境变量占位符"""
    placeholders = {}

    if isinstance(config_data, dict):
        for key, value in config_data.items():
            current_prefix = f"{prefix}.{key}" if prefix else key
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # 格式: ${VAR_NAME:default_value}
                placeholder = value[2:-1]  # 去掉 ${ 和 }
                if ':' in placeholder:
                    var_name, default_value = placeholder.split(':', 1)
                    placeholders[current_prefix] = {
                        'env_var': var_name,
                        'default': default_value
                    }
                else:
                    placeholders[current_prefix] = {
                        'env_var': placeholder,
                        'default': None
                    }
            elif isinstance(value, (dict, list)):
                placeholders.update(extract_env_placeholders(value, current_prefix))
    elif isinstance(config_data, list):
        for i, item in enumerate(config_data):
            current_prefix = f"{prefix}[{i}]"
            if isinstance(item, (dict, list)):
                placeholders.update(extract_env_placeholders(item, current_prefix))

    return placeholders


def validate_config():
    """主校验函数"""
    print("=" * 80)
    print("配置校验工具 - message_platform")
    print("=" * 80)

    # 1. 加载config.yaml
    config_path = project_root / "config.yaml"
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)

    print(f"✓ 加载配置文件: {config_path}")

    # 2. 加载.env
    env_path = project_root / ".env"
    env_vars = load_env_file(str(env_path))

    if env_vars:
        print(f"✓ 加载环境变量文件: {env_path} ({len(env_vars)} 个变量)")
    else:
        print(f"⚠️  未找到.env文件或文件为空")

    # 3. 提取占位符
    placeholders = extract_env_placeholders(config_data)
    print(f"\n✓ 检测到 {len(placeholders)} 个环境变量占位符\n")

    # 4. 分类分析
    print("=" * 80)
    print("配置详细分析")
    print("=" * 80)

    # LLM相关配置
    llm_keys = [k for k in placeholders.keys() if k.startswith('llm.')]
    if llm_keys:
        print("\n【LLM配置】")
        for key in sorted(llm_keys):
            info = placeholders[key]
            env_var = info['env_var']
            default_value = info['default']
            actual_value = env_vars.get(env_var, default_value)

            status = "✓" if env_var in env_vars else "⚠️ "
            source = ".env" if env_var in env_vars else "config.yaml默认值"

            print(f"\n  {status} {key}")
            print(f"     环境变量: {env_var}")
            print(f"     默认值: {default_value}")
            print(f"     实际值: {actual_value}")
            print(f"     来源: {source}")

            # 检查不一致
            if env_var in env_vars and env_vars[env_var] != default_value:
                print(f"     ⚠️  注意: .env中的值与config.yaml默认值不同")

    # 数据库相关配置
    db_keys = [k for k in placeholders.keys() if k.startswith('database.')]
    if db_keys:
        print("\n【数据库配置】")
        for key in sorted(db_keys):
            info = placeholders[key]
            env_var = info['env_var']
            default_value = info['default']
            actual_value = env_vars.get(env_var, default_value)

            status = "✓" if env_var in env_vars else "⚠️ "
            source = ".env" if env_var in env_vars else "config.yaml默认值"

            print(f"\n  {status} {key}")
            print(f"     环境变量: {env_var}")
            print(f"     实际值: {actual_value if key != 'database.mysql.password' else '******'}")
            print(f"     来源: {source}")

    # 总结
    print("\n" + "=" * 80)
    print("校验总结")
    print("=" * 80)

    env_overrides = sum(1 for info in placeholders.values() if info['env_var'] in env_vars)
    default_used = len(placeholders) - env_overrides

    print(f"  总配置项: {len(placeholders)}")
    print(f"  .env覆盖: {env_overrides}")
    print(f"  使用默认值: {default_used}")

    # 不一致检查
    inconsistencies = []
    for key, info in placeholders.items():
        env_var = info['env_var']
        default_value = info['default']
        if env_var in env_vars and env_vars[env_var] != default_value:
            inconsistencies.append(key)

    if inconsistencies:
        print(f"\n  ⚠️  发现 {len(inconsistencies)} 处配置不一致:")
        for key in inconsistencies:
            print(f"      - {key}")
        print(f"\n  建议: 更新config.yaml默认值与.env保持一致，避免误解")
    else:
        print(f"\n  ✓ 所有配置一致，无需调整")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        validate_config()
    except Exception as e:
        print(f"\n❌ 校验失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
