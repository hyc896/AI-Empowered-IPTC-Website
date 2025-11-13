# -*- coding: utf-8 -*-
"""
VentureBeat消息源注册脚本
自动执行register.sql中的SQL语句
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database.connection import init_database, create_session
from backend.config import get_global_config
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    """执行VentureBeat消息源注册"""

    logger.info("=" * 80)
    logger.info("VentureBeat消息源注册")
    logger.info("=" * 80)

    # 初始化数据库
    logger.info("\n✓ 初始化数据库连接...")
    init_database()

    # 读取SQL文件
    sql_file = os.path.join(
        os.path.dirname(__file__),
        'backend', 'sources', 'venturebeat', 'register.sql'
    )

    logger.info(f"✓ 读取SQL文件: {sql_file}")
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # 分割SQL语句（按分号分隔，忽略注释）
    sql_statements = []
    current_statement = []

    for line in sql_content.split('\n'):
        # 跳过注释行
        if line.strip().startswith('--') or not line.strip():
            continue

        current_statement.append(line)

        # 如果行以分号结尾，表示一条语句结束
        if line.strip().endswith(';'):
            sql_statements.append('\n'.join(current_statement))
            current_statement = []

    logger.info(f"✓ 解析到 {len(sql_statements)} 条SQL语句")

    # 执行SQL语句
    with create_session() as db:
        for i, sql in enumerate(sql_statements, 1):
            # 跳过空语句
            if not sql.strip():
                continue

            try:
                logger.info(f"\n[{i}/{len(sql_statements)}] 执行SQL...")

                # 执行SQL
                result = db.execute(sql)
                db.commit()

                # 显示结果
                if sql.strip().upper().startswith('SELECT'):
                    rows = result.fetchall()
                    if rows:
                        logger.info(f"  查询结果: {len(rows)} 行")
                        for row in rows:
                            logger.info(f"    {dict(row)}")
                    else:
                        logger.info("  查询结果: 0 行")
                elif sql.strip().upper().startswith('CREATE'):
                    logger.info("  ✓ 表创建成功")
                elif sql.strip().upper().startswith('INSERT'):
                    logger.info("  ✓ 数据插入成功")
                else:
                    logger.info("  ✓ 执行成功")

            except Exception as e:
                if "Duplicate entry" in str(e):
                    logger.info("  ℹ 记录已存在，已更新")
                elif "Table" in str(e) and "already exists" in str(e):
                    logger.info("  ℹ 表已存在，跳过创建")
                else:
                    logger.error(f"  ✗ 执行失败: {e}")
                    raise

    logger.info("\n" + "=" * 80)
    logger.info("✓ VentureBeat消息源注册完成")
    logger.info("=" * 80)

    # 验证注册结果
    logger.info("\n验证注册结果:")
    with create_session() as db:
        result = db.execute("""
            SELECT
                id,
                name,
                display_name,
                category,
                is_active,
                JSON_EXTRACT(config, '$.mysql_table') AS mysql_table,
                JSON_EXTRACT(config, '$.chroma_collection') AS chroma_collection,
                JSON_EXTRACT(config, '$.categories') AS categories
            FROM mp_message_sources
            WHERE name = 'venturebeat'
        """)

        row = result.fetchone()
        if row:
            logger.info(f"  消息源ID: {row[0]}")
            logger.info(f"  名称: {row[1]}")
            logger.info(f"  显示名称: {row[2]}")
            logger.info(f"  分类: {row[3]}")
            logger.info(f"  是否启用: {row[4]}")
            logger.info(f"  MySQL表: {row[5]}")
            logger.info(f"  ChromaDB集合: {row[6]}")
            logger.info(f"  栏目: {row[7]}")
        else:
            logger.error("  ✗ 未找到VentureBeat消息源，注册失败")
            return 1

    logger.info("\n✓ 注册验证成功！")
    return 0

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"\n✗ 注册失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
