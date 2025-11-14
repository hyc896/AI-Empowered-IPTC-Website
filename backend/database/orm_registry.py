# -*- coding: utf-8 -*-
"""
ORM类自动注册系统
新增ORM类时自动注册到全局Registry，无需手动维护映射表
"""

import logging
from typing import Dict, Type, Optional, List
from sqlalchemy.ext.declarative import DeclarativeMeta

logger = logging.getLogger(__name__)


class ORMRegistry:
    """
    ORM类注册中心

    功能：
    1. 自动发现和注册所有ORM类
    2. 提供表名 → ORM类的映射
    3. 启动时验证配置完整性
    """

    def __init__(self):
        self._registry: Dict[str, Type] = {}
        self._reverse_registry: Dict[Type, str] = {}

    def register(self, table_name: str, model_class: Type) -> None:
        """
        注册ORM类

        Args:
            table_name: 数据库表名
            model_class: ORM类
        """
        if table_name in self._registry:
            existing = self._registry[table_name]
            if existing != model_class:
                logger.warning(
                    f"表名冲突: {table_name} 已被 {existing.__name__} 注册，"
                    f"现在被 {model_class.__name__} 覆盖"
                )

        self._registry[table_name] = model_class
        self._reverse_registry[model_class] = table_name
        logger.debug(f"注册ORM类: {model_class.__name__} → {table_name}")

    def get_model(self, table_name: str) -> Optional[Type]:
        """
        根据表名获取ORM类

        Args:
            table_name: 数据库表名（支持带/不带前缀）

        Returns:
            ORM类，如果未找到返回None
        """
        return self._registry.get(table_name)

    def get_table_name(self, model_class: Type) -> Optional[str]:
        """根据ORM类获取表名"""
        return self._reverse_registry.get(model_class)

    def list_tables(self) -> List[str]:
        """列出所有已注册的表名"""
        return list(self._registry.keys())

    def list_models(self) -> List[Type]:
        """列出所有已注册的ORM类"""
        return list(self._reverse_registry.keys())

    def validate_table_name(self, table_name: str) -> bool:
        """验证表名是否已注册"""
        return table_name in self._registry

    def get_info(self) -> Dict[str, str]:
        """获取注册信息（用于调试）"""
        return {
            table: model.__name__
            for table, model in self._registry.items()
        }


# 全局单例
_orm_registry = ORMRegistry()


def register_orm_class(model_class: Type[DeclarativeMeta]) -> Type[DeclarativeMeta]:
    """
    装饰器：自动注册ORM类

    用法：
        @register_orm_class
        class TongHuaShunMessage(Base):
            __tablename__ = "mp_tonghuashun_messages"
    """
    if hasattr(model_class, '__tablename__'):
        table_name = model_class.__tablename__
        _orm_registry.register(table_name, model_class)
    else:
        logger.warning(f"ORM类 {model_class.__name__} 没有定义 __tablename__，跳过注册")

    return model_class


def get_orm_registry() -> ORMRegistry:
    """获取全局ORM注册中心"""
    return _orm_registry


def auto_register_all_models():
    """
    自动注册所有消息表（Message Tables）

    设计原则：
    - 消息表（*_messages）：动态绑定，通过Registry查询
    - 配置表（MessageSource等）：静态绑定，直接导入使用

    扫描entities模块，仅注册以_messages结尾的表
    """
    from . import entities
    import inspect

    logger.info("【ORM注册】开始自动扫描和注册消息表...")

    registered_count = 0
    skipped_count = 0

    for name, obj in inspect.getmembers(entities, inspect.isclass):
        # 检查是否有__tablename__和__table__属性（SQLAlchemy ORM类的特征）
        if hasattr(obj, '__tablename__') and hasattr(obj, '__table__'):
            table_name = obj.__tablename__

            # 只注册消息表（以_messages结尾）
            if table_name.endswith('_messages'):
                _orm_registry.register(table_name, obj)
                logger.info(f"【ORM注册】{name} → {table_name}")
                registered_count += 1
            else:
                logger.debug(f"【ORM注册】跳过非消息表: {name} → {table_name}")
                skipped_count += 1

    logger.info(f"【ORM注册】完成，共注册 {registered_count} 个消息表，跳过 {skipped_count} 个配置表")

    # 打印注册信息
    logger.info("【ORM注册】已注册的表名列表:")
    for table_name in sorted(_orm_registry.list_tables()):
        model = _orm_registry.get_model(table_name)
        logger.info(f"  - {table_name} → {model.__name__}")
