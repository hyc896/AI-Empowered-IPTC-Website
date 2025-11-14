# -*- coding: utf-8 -*-
"""
启动时配置验证
在应用启动时检查数据库配置与ORM定义的一致性
"""

import logging
from typing import List, Dict, Any
from sqlalchemy.exc import OperationalError

from .connection import create_session
from .entities import MessageSource
from .orm_registry import get_orm_registry

logger = logging.getLogger(__name__)


class ValidationResult:
    """验证结果"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def add_error(self, message: str):
        self.errors.append(f"{message}")
        logger.error(message)

    def add_warning(self, message: str):
        self.warnings.append(f"{message}")
        logger.warning(message)

    def add_info(self, message: str):
        self.info.append(f"{message}")
        logger.info(message)

    def is_valid(self) -> bool:
        """没有错误即为有效"""
        return len(self.errors) == 0

    def get_report(self) -> str:
        """生成验证报告"""
        lines = []
        lines.append("\n" + "="*70)
        lines.append("消息平台启动配置验证报告")
        lines.append("="*70)

        if self.info:
            lines.append("\n[OK] 验证通过:")
            lines.extend(f"  {msg}" for msg in self.info)

        if self.warnings:
            lines.append("\n[WARNING] 警告:")
            lines.extend(f"  {msg}" for msg in self.warnings)

        if self.errors:
            lines.append("\n[ERROR] 错误:")
            lines.extend(f"  {msg}" for msg in self.errors)
            lines.append("\n[FIX] 修复建议:")
            lines.append("  1. 检查 mp_message_sources 表中的 config.mysql_table 字段")
            lines.append("  2. 确保表名与 backend/database/entities.py 中的 __tablename__ 一致")
            lines.append("  3. 运行: python backend/scripts/fix_table_names.py")

        lines.append("="*70 + "\n")
        return "\n".join(lines)


def validate_message_sources() -> ValidationResult:
    """
    验证所有消息源配置

    检查项：
    1. 数据库中配置的表名是否有对应的ORM类
    2. ORM类的表名是否存在于数据库中
    3. ChromaDB collection名称是否规范
    """
    result = ValidationResult()
    registry = get_orm_registry()

    try:
        with create_session() as db:
            # 获取所有消息源
            sources = db.query(MessageSource).all()

            if not sources:
                result.add_warning("数据库中没有配置任何消息源")
                return result

            result.add_info(f"找到 {len(sources)} 个消息源配置")

            # 检查每个消息源
            for source in sources:
                source_name = source.display_name or source.name
                config = source.config or {}

                # 检查1：mysql_table字段是否存在
                if 'mysql_table' not in config:
                    result.add_error(
                        f"消息源 '{source_name}' 缺少 config.mysql_table 配置"
                    )
                    continue

                mysql_table = config['mysql_table']

                # 检查2：表名是否有对应的ORM类
                model = registry.get_model(mysql_table)
                if not model:
                    result.add_error(
                        f"消息源 '{source_name}' 配置的表名 '{mysql_table}' "
                        f"未找到对应的ORM类。"
                        f"已注册的表: {', '.join(registry.list_tables())}"
                    )
                else:
                    result.add_info(
                        f"消息源 '{source_name}' → 表 '{mysql_table}' → "
                        f"ORM类 {model.__name__}"
                    )

                # 检查3：ChromaDB collection名称
                if 'chroma_collection' not in config:
                    result.add_warning(
                        f"消息源 '{source_name}' 缺少 config.chroma_collection 配置"
                    )
                else:
                    chroma_collection = config['chroma_collection']
                    result.add_info(
                        f"消息源 '{source_name}' → ChromaDB集合 '{chroma_collection}'"
                    )

                # 检查4：是否启用
                if not source.is_active:
                    result.add_info(f"消息源 '{source_name}' 当前已禁用")

            # 检查未使用的消息表
            # 注意：Registry只包含消息表（*_messages），不包含配置表（MessageSource）
            registered_tables = set(registry.list_tables())
            configured_tables = {s.config.get('mysql_table') for s in sources if s.config.get('mysql_table')}
            unused_tables = registered_tables - configured_tables

            if unused_tables:
                result.add_warning(
                    f"以下消息表已定义但未被任何消息源使用: {', '.join(sorted(unused_tables))}"
                )

    except OperationalError as e:
        result.add_error(f"数据库连接失败: {e}")
    except Exception as e:
        result.add_error(f"验证过程中发生异常: {e}")

    return result


def startup_validation(fail_on_error: bool = True) -> bool:
    """
    启动时执行验证

    Args:
        fail_on_error: 如果为True，验证失败时抛出异常阻止启动

    Returns:
        验证是否通过
    """
    logger.info("【启动验证】开始启动配置验证...")

    # 自动注册所有ORM类
    from .orm_registry import auto_register_all_models
    auto_register_all_models()

    # 验证消息源配置
    result = validate_message_sources()

    # 打印报告
    print(result.get_report())

    if not result.is_valid():
        if fail_on_error:
            raise RuntimeError(
                "启动验证失败！请修复上述错误后重新启动。\n"
                "提示：可以设置环境变量 SKIP_VALIDATION=1 跳过验证（不推荐）"
            )
        return False

    logger.info("【启动验证】[OK] 启动配置验证通过！")
    return True
