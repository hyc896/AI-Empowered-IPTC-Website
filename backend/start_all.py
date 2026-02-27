# -*- coding: utf-8 -*-
"""
一体化启动脚本
管理FastAPI、Celery Worker、采集调度器和定时撞库任务
"""
import os
import sys
import time
import signal
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# 添加项目路径
backend_dir = Path(__file__).parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

# 创建日志目录
(backend_dir / 'logs').mkdir(exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(backend_dir / 'logs' / 'start_all.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class ProcessManager:
    """进程管理器"""

    def __init__(self):
        self.processes = {}
        self.scheduler = BackgroundScheduler()
        self.running = False

    def start_fastapi(self):
        """启动FastAPI服务"""
        logger.info("【启动】FastAPI服务...")
        cmd = [
            sys.executable, "-m", "uvicorn",
            "backend.main:app",
            "--host", "0.0.0.0",
            "--port", "11528"
        ]
        # 创建日志文件
        log_file = open(backend_dir / 'logs' / 'fastapi.log', 'a', encoding='utf-8')
        process = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=log_file,
            stderr=subprocess.STDOUT
        )
        self.processes['fastapi'] = process
        self.log_files = getattr(self, 'log_files', {})
        self.log_files['fastapi'] = log_file
        logger.info(f"✓ FastAPI服务已启动 (PID: {process.pid})")
        return process

    def start_celery_worker(self):
        """启动Celery Worker"""
        logger.info("【启动】Celery Worker...")
        cmd = [
            sys.executable, "-m", "celery",
            "-A", "backend.tasks",
            "worker",
            "--loglevel=info",
            "--pool=solo"
        ]
        # 创建日志文件
        log_file = open(backend_dir / 'logs' / 'celery_worker.log', 'a', encoding='utf-8')
        process = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=log_file,
            stderr=subprocess.STDOUT
        )
        self.processes['celery_worker'] = process
        self.log_files = getattr(self, 'log_files', {})
        self.log_files['celery_worker'] = log_file
        logger.info(f"✓ Celery Worker已启动 (PID: {process.pid})")
        return process

    def start_collector_scheduler(self):
        """启动采集调度器"""
        logger.info("【启动】采集调度器...")
        cmd = [
            sys.executable,
            str(backend_dir / "scripts" / "iptc_auto_scheduler.py")
        ]
        # 创建日志文件
        log_file = open(backend_dir / 'logs' / 'collector_scheduler.log', 'a', encoding='utf-8')
        process = subprocess.Popen(
            cmd,
            cwd=str(backend_dir),
            stdout=log_file,
            stderr=subprocess.STDOUT
        )
        self.processes['collector_scheduler'] = process
        self.log_files = getattr(self, 'log_files', {})
        self.log_files['collector_scheduler'] = log_file
        logger.info(f"✓ 采集调度器已启动 (PID: {process.pid})")
        return process

    def run_batch_match_cases(self):
        """执行撞库生成案例任务"""
        logger.info("="*60)
        logger.info("【定时任务】开始执行撞库生成案例...")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            cmd = [
                sys.executable,
                str(backend_dir / "scripts" / "batch_match_cases.py")
            ]
            result = subprocess.run(
                cmd,
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
                timeout=7200  # 2小时超时
            )

            if result.returncode == 0:
                logger.info("✓ 撞库任务执行成功")
                logger.info(f"输出: {result.stdout[-500:]}")  # 只记录最后500字符
            else:
                logger.error(f"✗ 撞库任务执行失败 (返回码: {result.returncode})")
                logger.error(f"错误: {result.stderr}")

        except subprocess.TimeoutExpired:
            logger.error("✗ 撞库任务超时（超过2小时）")
        except Exception as e:
            logger.error(f"✗ 撞库任务执行异常: {e}")

        logger.info("="*60)

    def backup_chromadb(self):
        """备份ChromaDB数据"""
        logger.info("="*60)
        logger.info("【定时任务】开始备份ChromaDB数据...")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            cmd = [
                sys.executable,
                str(backend_dir / "scripts" / "backup_chromadb.py"),
                "--backup",
                "--max-backups", "7"  # 保留最近7个备份
            ]
            result = subprocess.run(
                cmd,
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )

            if result.returncode == 0:
                logger.info("✓ ChromaDB备份成功")
            else:
                logger.error(f"✗ ChromaDB备份失败 (返回码: {result.returncode})")
                logger.error(f"错误: {result.stderr}")

        except subprocess.TimeoutExpired:
            logger.error("✗ ChromaDB备份超时")
        except Exception as e:
            logger.error(f"✗ ChromaDB备份异常: {e}")

        logger.info("="*60)

    def setup_scheduled_tasks(self):
        """设置定时任务"""
        # 每半天（12小时）执行一次撞库任务
        self.scheduler.add_job(
            self.run_batch_match_cases,
            trigger=IntervalTrigger(hours=12),
            id='batch_match_cases',
            name='批量撞库生成案例',
            replace_existing=True
        )
        logger.info("✓ 定时任务已配置：每12小时执行一次撞库")

        # 每天凌晨3点备份ChromaDB数据
        from apscheduler.triggers.cron import CronTrigger
        self.scheduler.add_job(
            self.backup_chromadb,
            trigger=CronTrigger(hour=3, minute=0),
            id='backup_chromadb',
            name='备份ChromaDB数据',
            replace_existing=True
        )
        logger.info("✓ 定时任务已配置：每天凌晨3点备份ChromaDB")

        # 启动调度器
        self.scheduler.start()
        logger.info("✓ 定时调度器已启动")

    def monitor_processes(self):
        """监控进程状态"""
        while self.running:
            for name, process in list(self.processes.items()):
                if process.poll() is not None:
                    logger.warning(f"⚠ 进程 {name} 已退出 (返回码: {process.returncode})")
                    # 可以在这里添加自动重启逻辑
            time.sleep(10)  # 每10秒检查一次

    def start_all(self):
        """启动所有服务"""
        logger.info("="*60)
        logger.info("开始启动所有服务...")
        logger.info("="*60)

        try:
            # 创建日志目录
            (backend_dir / 'logs').mkdir(exist_ok=True)

            # 启动各个服务
            self.start_fastapi()
            time.sleep(3)  # 等待FastAPI启动

            self.start_celery_worker()
            time.sleep(3)  # 等待Celery启动

            self.start_collector_scheduler()
            time.sleep(2)

            # 设置定时任务
            self.setup_scheduled_tasks()

            # 启动时立即执行一轮撞库任务
            logger.info("="*60)
            logger.info("【初始化】启动时执行首次撞库任务...")
            logger.info("="*60)
            time.sleep(5)  # 等待采集调度器完成首次采集
            self.run_batch_match_cases()

            self.running = True
            logger.info("="*60)
            logger.info("✓ 所有服务启动完成！")
            logger.info("="*60)
            logger.info("运行中的服务:")
            for name, process in self.processes.items():
                logger.info(f"  - {name}: PID {process.pid}")
            logger.info("="*60)

            # 监控进程
            self.monitor_processes()

        except KeyboardInterrupt:
            logger.info("\n收到中断信号，正在关闭所有服务...")
            self.stop_all()
        except Exception as e:
            logger.error(f"启动失败: {e}")
            self.stop_all()
            raise

    def stop_all(self):
        """停止所有服务"""
        logger.info("正在停止所有服务...")

        self.running = False

        # 停止调度器
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("✓ 定时调度器已停止")

        # 停止所有进程
        for name, process in self.processes.items():
            if process.poll() is None:
                logger.info(f"正在停止 {name}...")
                process.terminate()
                try:
                    process.wait(timeout=10)
                    logger.info(f"✓ {name} 已停止")
                except subprocess.TimeoutExpired:
                    logger.warning(f"⚠ {name} 未响应，强制终止")
                    process.kill()

        # 关闭所有日志文件
        for name, log_file in getattr(self, 'log_files', {}).items():
            try:
                log_file.close()
                logger.info(f"✓ {name} 日志文件已关闭")
            except Exception as e:
                logger.warning(f"⚠ 关闭 {name} 日志文件失败: {e}")

        logger.info("✓ 所有服务已停止")


def main():
    """主函数"""
    manager = ProcessManager()

    # 注册信号处理
    def signal_handler(signum, frame):
        logger.info(f"\n收到信号 {signum}，正在关闭...")
        manager.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 启动所有服务
    manager.start_all()


if __name__ == "__main__":
    main()
