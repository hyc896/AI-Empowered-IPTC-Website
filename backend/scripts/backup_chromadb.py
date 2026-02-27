# -*- coding: utf-8 -*-
"""
ChromaDB数据备份脚本
定期备份ChromaDB数据，防止数据损坏导致的数据丢失
"""
import os
import shutil
import sys
from pathlib import Path
from datetime import datetime
import logging

# 添加backend目录到path
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def backup_chromadb(max_backups=5):
    """
    备份ChromaDB数据

    Args:
        max_backups: 保留的最大备份数量
    """
    try:
        # ChromaDB数据路径
        chromadb_path = project_root / "data" / "chromadb_mp"

        if not chromadb_path.exists():
            logger.warning(f"ChromaDB数据目录不存在: {chromadb_path}")
            return False

        # 备份目录
        backup_dir = project_root / "data" / "chromadb_backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # 生成备份文件名（带时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"chromadb_backup_{timestamp}"
        backup_path = backup_dir / backup_name

        logger.info("="*60)
        logger.info("开始备份ChromaDB数据...")
        logger.info(f"源路径: {chromadb_path}")
        logger.info(f"备份路径: {backup_path}")

        # 复制整个目录
        shutil.copytree(chromadb_path, backup_path)

        logger.info(f"✓ 备份完成: {backup_name}")

        # 清理旧备份（保留最近的N个）
        cleanup_old_backups(backup_dir, max_backups)

        logger.info("="*60)
        return True

    except Exception as e:
        logger.error(f"✗ 备份失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def cleanup_old_backups(backup_dir, max_backups):
    """
    清理旧备份，只保留最近的N个

    Args:
        backup_dir: 备份目录
        max_backups: 保留的最大备份数量
    """
    try:
        # 获取所有备份目录
        backups = [d for d in backup_dir.iterdir() if d.is_dir() and d.name.startswith("chromadb_backup_")]

        # 按时间排序（最新的在前）
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # 删除多余的备份
        if len(backups) > max_backups:
            logger.info(f"清理旧备份（保留最近{max_backups}个）...")
            for old_backup in backups[max_backups:]:
                logger.info(f"  删除: {old_backup.name}")
                shutil.rmtree(old_backup)
            logger.info(f"✓ 清理完成，当前备份数: {max_backups}")
        else:
            logger.info(f"当前备份数: {len(backups)}/{max_backups}")

    except Exception as e:
        logger.error(f"清理旧备份失败: {e}")


def restore_from_backup(backup_name=None):
    """
    从备份恢复ChromaDB数据

    Args:
        backup_name: 备份名称，如果为None则使用最新的备份
    """
    try:
        backup_dir = project_root / "data" / "chromadb_backups"

        if not backup_dir.exists():
            logger.error("备份目录不存在")
            return False

        # 获取所有备份
        backups = [d for d in backup_dir.iterdir() if d.is_dir() and d.name.startswith("chromadb_backup_")]

        if not backups:
            logger.error("没有可用的备份")
            return False

        # 选择备份
        if backup_name:
            backup_path = backup_dir / backup_name
            if not backup_path.exists():
                logger.error(f"指定的备份不存在: {backup_name}")
                return False
        else:
            # 使用最新的备份
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            backup_path = backups[0]

        logger.info("="*60)
        logger.info("开始从备份恢复ChromaDB数据...")
        logger.info(f"备份: {backup_path.name}")

        # 目标路径
        chromadb_path = project_root / "data" / "chromadb_mp"

        # 如果目标存在，先删除
        if chromadb_path.exists():
            logger.info("删除现有的ChromaDB数据...")
            shutil.rmtree(chromadb_path)

        # 从备份恢复
        shutil.copytree(backup_path, chromadb_path)

        logger.info(f"✓ 恢复完成")
        logger.info("="*60)
        return True

    except Exception as e:
        logger.error(f"✗ 恢复失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ChromaDB数据备份和恢复工具")
    parser.add_argument("--backup", action="store_true", help="执行备份")
    parser.add_argument("--restore", action="store_true", help="从备份恢复")
    parser.add_argument("--backup-name", type=str, help="指定要恢复的备份名称")
    parser.add_argument("--max-backups", type=int, default=5, help="保留的最大备份数量")

    args = parser.parse_args()

    if args.backup:
        backup_chromadb(max_backups=args.max_backups)
    elif args.restore:
        restore_from_backup(backup_name=args.backup_name)
    else:
        print("请指定操作: --backup 或 --restore")
        parser.print_help()
