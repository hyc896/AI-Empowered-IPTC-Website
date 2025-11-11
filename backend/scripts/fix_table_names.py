# -*- coding: utf-8 -*-
"""
修复数据库配置中的表名错误
一键修正config.mysql_table字段，使其与entities.py中的__tablename__一致
使用ORM Registry自动发现有效表名，零硬编码
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import logging
from backend.database.connection import create_session
from backend.database.entities import MessageSource
from backend.database.orm_registry import get_orm_registry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_table_names():
    """
    修正所有消息源的表名配置

    智能修复策略：
    1. 从ORM Registry获取所有有效表名（自动发现，无硬编码）
    2. 如果当前表名无效，尝试添加mp_前缀修复
    3. 使用新字典对象更新，确保SQLAlchemy检测到JSON字段变化
    """
    try:
        # 初始化ORM Registry，获取所有有效表名
        registry = get_orm_registry()
        from backend.database.orm_registry import auto_register_all_models
        auto_register_all_models()

        valid_tables = set(registry.list_tables())
        logger.info(f"ORM Registry中有效表名: {sorted(valid_tables)}\n")

        with create_session() as db:
            sources = db.query(MessageSource).all()
            logger.info(f"找到 {len(sources)} 个消息源配置\n")

            fixed_count = 0

            for source in sources:
                config = source.config or {}
                current_table = config.get('mysql_table')

                if not current_table:
                    logger.warning(f"⚠️  消息源 '{source.display_name}' 缺少 mysql_table 配置，跳过")
                    continue

                # 检查当前表名是否有效
                if current_table in valid_tables:
                    logger.info(f"✓ 消息源 '{source.display_name}' 表名正确: {current_table}")
                    continue

                # 尝试智能修复：添加mp_前缀
                fixed_table = f"mp_{current_table}"

                if fixed_table in valid_tables:
                    logger.info(
                        f"🔧 修正消息源 '{source.display_name}': "
                        f"'{current_table}' → '{fixed_table}'"
                    )

                    # 创建新字典对象（强制SQLAlchemy检测到JSON字段变化）
                    new_config = dict(config)
                    new_config['mysql_table'] = fixed_table
                    source.config = new_config

                    fixed_count += 1
                else:
                    logger.error(
                        f"❌ 消息源 '{source.display_name}' 的表名 '{current_table}' 无法修复\n"
                        f"   尝试的修复名 '{fixed_table}' 也不在Registry中\n"
                        f"   可能需要在entities.py中创建对应的ORM类"
                    )

            # 统一提交所有修改
            db.commit()

            logger.info(f"\n{'='*70}")
            logger.info(f"修正完成！共修正 {fixed_count} 个消息源配置")
            logger.info(f"{'='*70}\n")

            # 验证修正结果
            logger.info("验证修正结果：")
            sources = db.query(MessageSource).all()
            for source in sources:
                config = source.config or {}
                table_name = config.get('mysql_table', '(未配置)')
                status = "✓" if table_name in valid_tables else "✗"
                logger.info(f"  {status} {source.display_name}: {table_name}")

    except Exception as e:
        logger.error(f"修正过程中发生错误: {e}", exc_info=True)
        return False

    return True


if __name__ == "__main__":
    logger.info("="*70)
    logger.info("开始修正数据库配置中的表名错误（智能修复）")
    logger.info("="*70)

    success = fix_table_names()

    if success:
        logger.info("\n✅ 表名修正完成！请重启服务以验证修复效果。")
    else:
        logger.error("\n❌ 表名修正失败，请查看上面的错误信息")
        sys.exit(1)
