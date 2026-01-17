# -*- coding: utf-8 -*-
"""
IPTC案例自动生成调度器
定时从数据库读取新消息，进行向量匹配并生成案例

说明：
- 采集器已通过各自的interval配置自动运行，无需手动触发
- 本调度器专注于案例生成：消息→向量匹配→案例生成→存储

启动方式：
    # 正常模式（每小时执行一次）
    python backend/scripts/iptc_auto_scheduler.py

    # 测试模式（只执行一次，限制数据量）
    python backend/scripts/iptc_auto_scheduler.py --test

    # 仅测试初始化
    python backend/scripts/iptc_auto_scheduler.py --init-only

停止方式：
    Ctrl+C 或 kill进程
"""
import sys
import os
import time
import logging
import schedule
import argparse
from pathlib import Path
from datetime import datetime

# 添加backend目录到path
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

from database.connection import init_database
from backend.scripts.batch_match_cases import BatchMatchCasesService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/iptc_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class IPTCAutoScheduler:
    """IPTC案例自动生成调度器"""

    def __init__(self, test_mode: bool = False):
        """
        初始化调度器

        Args:
            test_mode: 测试模式，限制数据量，只执行一次
        """
        self.logger = logger
        self.test_mode = test_mode

    def initialize(self):
        """初始化服务"""
        try:
            # 初始化数据库
            if not init_database():
                raise Exception("数据库初始化失败")
            self.logger.info("✅ 数据库初始化成功")

        except Exception as e:
            self.logger.error(f"❌ 初始化失败: {e}")
            raise

    def run_case_generation_task(self):
        """执行案例生成任务：向量匹配 → 生成案例"""
        self.logger.info("=" * 60)
        self.logger.info(f"[定时任务] 开始案例生成 - {datetime.now()}")
        self.logger.info("=" * 60)

        try:
            # 初始化案例生成服务
            service = BatchMatchCasesService()

            # 执行撞库和案例生成
            if self.test_mode:
                # 测试模式：限制处理5条消息
                self.logger.info("[测试模式] 限制处理5条消息")
                service.run_batch_match(limit=5, dry_run=False)
            else:
                # 正常模式：处理所有新消息
                service.run_batch_match(limit=None, dry_run=False)

            self.logger.info("✅ [案例生成] 任务完成")

        except Exception as e:
            self.logger.error(f"❌ [案例生成] 任务异常: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    def run_hourly_task(self):
        """每小时执行的任务：从数据库读取新消息并生成案例"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info(f"🚀 开始执行定时任务 - {datetime.now()}")
        self.logger.info("=" * 80)

        start_time = time.time()

        try:
            # 执行案例生成
            self.run_case_generation_task()

            elapsed = time.time() - start_time
            self.logger.info("=" * 80)
            self.logger.info(f"✅ 定时任务完成 - 耗时 {elapsed:.2f}秒")
            self.logger.info("=" * 80 + "\n")

        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.error("=" * 80)
            self.logger.error(f"❌ 定时任务失败 - 耗时 {elapsed:.2f}秒 - {e}")
            self.logger.error("=" * 80 + "\n")

    def start(self):
        """启动调度器"""
        self.logger.info("=" * 80)
        self.logger.info("🎯 IPTC案例自动生成调度器启动")
        self.logger.info("=" * 80)

        if self.test_mode:
            self.logger.info(f"模式: 测试模式（只执行一次）")
        else:
            self.logger.info(f"模式: 正常模式（每小时执行一次）")

        self.logger.info(f"首次执行: 立即开始")
        self.logger.info("=" * 80 + "\n")

        if self.test_mode:
            # 测试模式：只执行一次
            self.logger.info("⏰ 测试模式：执行一次任务...")
            self.run_hourly_task()
            self.logger.info("✅ 测试完成，退出")
            return

        # 正常模式：设置定时任务
        schedule.every().hour.do(self.run_hourly_task)

        # 立即执行一次
        self.logger.info("⏰ 立即执行首次任务...")
        self.run_hourly_task()

        # 持续运行调度器
        self.logger.info("📅 进入定时循环，等待下次执行（每小时）...\n")
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次

        except KeyboardInterrupt:
            self.logger.info("\n" + "=" * 80)
            self.logger.info("⏹️  收到停止信号，正在关闭调度器...")
            self.logger.info("=" * 80)

    def stop(self):
        """停止调度器"""
        self.logger.info("✅ 调度器已停止")


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='IPTC案例自动生成调度器')
    parser.add_argument('--test', action='store_true', help='测试模式（只执行一次，限制数据量）')
    parser.add_argument('--init-only', action='store_true', help='仅测试初始化，不执行任务')
    args = parser.parse_args()

    # 创建logs目录
    os.makedirs('logs', exist_ok=True)

    # 创建调度器
    scheduler = IPTCAutoScheduler(test_mode=args.test)

    # 初始化
    scheduler.initialize()

    if args.init_only:
        logger.info("=" * 80)
        logger.info("✅ 初始化测试完成")
        logger.info("=" * 80)
        logger.info("\n说明：")
        logger.info("  - 采集器通过各自的interval配置自动运行")
        logger.info("  - 本调度器每小时执行一次案例生成任务")
        logger.info("  - 使用 'python backend/scripts/iptc_auto_scheduler.py' 启动")
        return

    # 启动调度器
    scheduler.start()


if __name__ == "__main__":
    main()
