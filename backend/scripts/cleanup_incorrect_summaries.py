# -*- coding: utf-8 -*-

"""
错误Summary清理脚本

清理5个错误消息源的summary字段和ChromaDB数据：
- RAND
- OECD AI
- GovAI
- CSIS
- CSET

使用方法：
    python backend/scripts/cleanup_incorrect_summaries.py --dry-run --source all
    python backend/scripts/cleanup_incorrect_summaries.py --source rand
"""

import sys
import os
import argparse
import logging
from typing import List, Dict

# 添加项目根目录到路径（需要找到backend模块）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.database.connection import create_session
from backend.database.entities import MessageSource
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# 需要清理的消息源配置
SOURCES_TO_CLEAN = {
    'rand': {
        'name': 'RAND Corporation',
        'mysql_table': 'mp_rand_messages',
        'chroma_collection': 'rand_research'
    },
    'oecd': {
        'name': 'OECD AI Policy Observatory',
        'mysql_table': 'mp_oecd_ai_messages',
        'chroma_collection': 'oecd_ai_policy'
    },
    'govai': {
        'name': 'GovAI',
        'mysql_table': 'mp_govai_messages',
        'chroma_collection': 'govai_papers'
    },
    'csis': {
        'name': 'CSIS',
        'mysql_table': 'mp_csis_messages',
        'chroma_collection': 'csis_analysis'
    },
    'cset': {
        'name': 'CSET Georgetown',
        'mysql_table': 'mp_cset_messages',
        'chroma_collection': 'cset_publications'
    }
}


def get_sources_to_process(source_arg: str) -> List[Dict]:
    """
    获取需要处理的消息源列表

    Args:
        source_arg: 命令行参数（'all'或具体源名）

    Returns:
        消息源配置列表
    """
    if source_arg == 'all':
        return list(SOURCES_TO_CLEAN.values())
    elif source_arg in SOURCES_TO_CLEAN:
        return [SOURCES_TO_CLEAN[source_arg]]
    else:
        raise ValueError(f"未知的消息源: {source_arg}")


def count_records(mysql_table: str) -> int:
    """
    统计MySQL表中的记录数

    Args:
        mysql_table: MySQL表名

    Returns:
        记录总数
    """
    try:
        with create_session() as db:
            result = db.execute(text(f"SELECT COUNT(*) FROM {mysql_table}"))
            count = result.scalar()
            return count
    except Exception as e:
        logger.error(f"统计{mysql_table}记录数失败: {e}")
        return 0


def clear_mysql_summaries(mysql_table: str, dry_run: bool = False) -> int:
    """
    清理MySQL表中的summary字段（设为空字符串）

    Args:
        mysql_table: MySQL表名
        dry_run: 是否为试运行模式

    Returns:
        清理的记录数
    """
    try:
        with create_session() as db:
            # 统计将要清理的记录数
            result = db.execute(text(f"SELECT COUNT(*) FROM {mysql_table} WHERE summary IS NOT NULL AND summary != ''"))
            count = result.scalar()

            if dry_run:
                logger.info(f"  [DRY RUN] 将清理 {count} 条记录的summary字段")
                return count

            # 执行清理：将summary设为空字符串
            db.execute(text(f"UPDATE {mysql_table} SET summary = ''"))
            db.commit()

            logger.info(f"  ✓ 已清理 {count} 条记录的summary字段")
            return count

    except Exception as e:
        logger.error(f"  ✗ 清理{mysql_table}的summary失败: {e}")
        return 0


def delete_chroma_collection(chroma_collection: str, dry_run: bool = False) -> bool:
    """
    删除ChromaDB collection

    Args:
        chroma_collection: ChromaDB collection名称
        dry_run: 是否为试运行模式

    Returns:
        是否成功
    """
    try:
        from backend.storage import get_chromadb_storage
        chroma_storage = get_chromadb_storage()

        # 检查是否已初始化
        if not chroma_storage.is_initialized():
            logger.warning(f"  ⚠ ChromaDB未初始化，跳过删除: {chroma_collection}")
            return True

        # 获取collection文档数量
        count = chroma_storage.get_collection_count(chroma_collection)

        if dry_run:
            logger.info(f"  [DRY RUN] 将删除ChromaDB collection: {chroma_collection} ({count}条向量数据)")
            return True

        # 删除collection
        success = chroma_storage.delete_collection(chroma_collection)
        if success:
            logger.info(f"  ✓ 已删除ChromaDB collection: {chroma_collection} ({count}条向量数据)")
        return success

    except ImportError:
        logger.warning(f"  ⚠ ChromaDB不可用，跳过向量数据清理")
        return False
    except Exception as e:
        logger.error(f"  ✗ 删除ChromaDB collection失败: {e}")
        return False


def recreate_chroma_collection(chroma_collection: str, dry_run: bool = False) -> bool:
    """
    重新创建ChromaDB collection（空集合）

    Args:
        chroma_collection: ChromaDB collection名称
        dry_run: 是否为试运行模式

    Returns:
        是否成功
    """
    if dry_run:
        logger.info(f"  [DRY RUN] 将重新创建ChromaDB collection: {chroma_collection}")
        return True

    try:
        from backend.storage import get_chromadb_storage
        chroma_storage = get_chromadb_storage()

        # 检查是否已初始化
        if not chroma_storage.is_initialized():
            logger.warning(f"  ⚠ ChromaDB未初始化，跳过重新创建: {chroma_collection}")
            return True

        # 重新创建collection
        success = chroma_storage.create_collection(chroma_collection)
        if success:
            logger.info(f"  ✓ 已重新创建ChromaDB collection: {chroma_collection}")
        return success

    except ImportError:
        logger.warning(f"  ⚠ ChromaDB不可用，跳过重新创建")
        return False
    except Exception as e:
        logger.error(f"  ✗ 重新创建ChromaDB collection失败: {e}")
        return False


def init_chromadb():
    """初始化ChromaDB（如果可用）"""
    try:
        from backend.storage import get_chromadb_storage
        from backend.config import ConfigManager

        # 使用ConfigManager加载配置（会自动解析环境变量）
        config_manager = ConfigManager()
        config_manager.load_config('config.yaml')
        config = config_manager.get_config()

        # 获取ChromaDB配置
        chroma_config = config.get('database', {}).get('chromadb', {})

        if not chroma_config:
            logger.warning("⚠ config.yaml中未找到database.chromadb配置，跳过ChromaDB初始化")
            return False

        # 初始化ChromaDB
        chroma_storage = get_chromadb_storage()
        success = chroma_storage.initialize(chroma_config)

        if success:
            logger.info("✓ ChromaDB初始化成功")
        else:
            logger.warning("⚠ ChromaDB初始化失败，将跳过向量数据清理")

        return success

    except Exception as e:
        logger.warning(f"⚠ ChromaDB初始化失败: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='清理错误的summary数据')
    parser.add_argument(
        '--source',
        choices=['rand', 'oecd', 'govai', 'csis', 'cset', 'all'],
        required=True,
        help='指定要清理的消息源（all表示全部）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='试运行模式，仅预览影响范围，不实际执行清理'
    )

    args = parser.parse_args()

    # 初始化ChromaDB（非dry-run模式才需要）
    if not args.dry_run:
        init_chromadb()

    # 获取需要处理的消息源
    try:
        sources = get_sources_to_process(args.source)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    # 打印清理计划
    logger.info("=" * 60)
    if args.dry_run:
        logger.info("清理影响预览（DRY RUN模式）")
    else:
        logger.info("开始清理错误的summary数据")
    logger.info("=" * 60)

    # 统计总影响
    total_records = 0
    for source in sources:
        count = count_records(source['mysql_table'])
        total_records += count
        logger.info(f"\n【{source['name']}】")
        logger.info(f"  MySQL表: {source['mysql_table']}")
        logger.info(f"  ChromaDB collection: {source['chroma_collection']}")
        logger.info(f"  记录数: {count} 条")

    logger.info("\n" + "=" * 60)
    logger.info(f"总计: {total_records} 条记录将受影响")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("\n[DRY RUN] 这是试运行模式，不会实际修改数据")
        logger.info("[DRY RUN] 移除--dry-run参数后重新运行以执行实际清理")
        return

    # 确认清理
    confirm = input("\n确认要清理这些数据吗？(yes/no): ")
    if confirm.lower() != 'yes':
        logger.info("已取消清理操作")
        return

    # 执行清理
    logger.info("\n开始执行清理...\n")

    for source in sources:
        logger.info(f"【{source['name']}】")

        # 1. 清理MySQL summary字段
        clear_mysql_summaries(source['mysql_table'], dry_run=False)

        # 2. 删除ChromaDB collection
        delete_chroma_collection(source['chroma_collection'], dry_run=False)

        # 3. 重新创建空collection
        recreate_chroma_collection(source['chroma_collection'], dry_run=False)

        logger.info("")

    logger.info("=" * 60)
    logger.info("清理完成！")
    logger.info("=" * 60)
    logger.info("\n下一步操作：")
    logger.info("1. 重启message_platform服务")
    logger.info("2. 采集器将自动重新采集数据并正确翻译")
    logger.info("3. 或运行批量重新翻译脚本：python backend/scripts/retranslate_summaries.py")


if __name__ == '__main__':
    main()
