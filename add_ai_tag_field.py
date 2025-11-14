# -*- coding: utf-8 -*-
"""
添加ai_tag字段迁移脚本
为mp_tonghuashun_messages和mp_kr36_messages表添加ai_tag字段
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.connection import init_database, create_session
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    """执行数据库迁移"""

    logger.info("=" * 80)
    logger.info("添加ai_tag字段数据库迁移")
    logger.info("=" * 80)

    # 初始化数据库连接
    logger.info("\n[1/3] 初始化数据库连接...")
    init_database()

    with create_session() as db:
        # 1. 检查字段是否已存在
        logger.info("\n[2/3] 检查现有字段...")

        tables_to_update = [
            'mp_tonghuashun_messages',
            'mp_kr36_messages'
        ]

        for table_name in tables_to_update:
            # 检查字段是否存在
            result = db.execute(text(f"""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = '{table_name}'
                  AND COLUMN_NAME = 'ai_tag'
            """))

            count = result.fetchone()[0]

            if count > 0:
                logger.info(f"  ✓ {table_name}.ai_tag 字段已存在，跳过")
                continue

            # 添加字段
            logger.info(f"\n[3/3] 为 {table_name} 添加ai_tag字段...")

            try:
                db.execute(text(f"""
                    ALTER TABLE `{table_name}`
                    ADD COLUMN `ai_tag` VARCHAR(50) NULL
                    COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）'
                    AFTER `industry_tags`
                """))

                db.commit()
                logger.info(f"  ✓ {table_name}.ai_tag 字段添加成功")

            except Exception as e:
                db.rollback()
                logger.error(f"  ✗ {table_name}.ai_tag 字段添加失败: {e}")
                raise

    logger.info("\n" + "=" * 80)
    logger.info("✓ 数据库迁移完成！")
    logger.info("=" * 80)

    # 验证结果
    logger.info("\n验证迁移结果:")
    with create_session() as db:
        for table_name in tables_to_update:
            result = db.execute(text(f"""
                SHOW COLUMNS FROM `{table_name}` LIKE 'ai_tag'
            """))

            row = result.fetchone()
            if row:
                logger.info(f"  ✓ {table_name}.ai_tag: {row[1]} ({row[4]})")
            else:
                logger.error(f"  ✗ {table_name}.ai_tag: 字段不存在")

    logger.info("\n提示：重启消息平台服务以加载新字段")
    logger.info("  python backend/main.py")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"\n✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
