# -*- coding: utf-8 -*-

"""
消息平台统一启动脚本

启动顺序：
1. ChromaDB Server (端口11530)
2. 采集器 Worker (监听 default,collector 队列)
3. 日报 Worker (监听 report 队列)
4. Celery Beat (定时调度)
5. FastAPI Server (端口11528)

使用方式：
    python start.py
"""

import subprocess
import sys
import time
import signal
import os
from typing import List

# 进程列表（用于清理）
processes: List[subprocess.Popen] = []


def start_process(name: str, cmd: List[str], wait_seconds: int = 2) -> subprocess.Popen:
    """启动子进程"""
    print(f"\n{'='*50}")
    print(f"启动 {name}...")
    print(f"命令: {' '.join(cmd)}")
    print(f"{'='*50}")

    proc = subprocess.Popen(
        cmd,
        stdout=sys.stdout,
        stderr=sys.stderr,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
    )
    processes.append(proc)

    time.sleep(wait_seconds)

    if proc.poll() is not None:
        print(f"[错误] {name} 启动失败，退出码: {proc.returncode}")
        cleanup()
        sys.exit(1)

    print(f"[成功] {name} 已启动 (PID: {proc.pid})")
    return proc


def cleanup():
    """清理所有子进程"""
    print("\n\n正在关闭所有服务...")
    for proc in reversed(processes):
        if proc.poll() is None:
            try:
                if sys.platform == 'win32':
                    proc.terminate()
                else:
                    proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=5)
                print(f"  - PID {proc.pid} 已关闭")
            except Exception as e:
                print(f"  - PID {proc.pid} 强制终止: {e}")
                proc.kill()
    print("所有服务已关闭")


def signal_handler(signum, frame):
    """信号处理"""
    cleanup()
    sys.exit(0)


def main():
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 切换到项目根目录
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    print("="*60)
    print("       消息平台 (Message Platform) 启动中...")
    print("="*60)
    print(f"工作目录: {project_root}")
    print(f"Python: {sys.executable}")

    try:
        # 1. 启动 ChromaDB Server
        start_process(
            "ChromaDB Server",
            ["chroma", "run",
             "--path", "./data/chromadb",
             "--host", "0.0.0.0",
             "--port", "11530"],
            wait_seconds=3
        )

        # 2. 启动采集器 Worker（监听 default,collector 队列）
        start_process(
            "采集器 Worker",
            ["celery", "-A", "backend.tasks", "worker",
             "--loglevel=info",
             "--pool=solo",
             "-Q", "default,collector",
             "-n", "collector@%h"],
            wait_seconds=5
        )

        # 3. 启动日报 Worker（监听 report 队列，独立处理日报生成任务）
        start_process(
            "日报 Worker",
            ["celery", "-A", "backend.tasks", "worker",
             "--loglevel=info",
             "--pool=solo",
             "-Q", "report",
             "-n", "report@%h"],
            wait_seconds=3
        )

        # 4. 启动 Celery Beat（使用无状态调度器，每次启动从代码读取配置）
        start_process(
            "Celery Beat",
            ["celery", "-A", "backend.tasks", "beat",
             "--loglevel=info",
             "--scheduler=celery.beat.Scheduler"],
            wait_seconds=2
        )

        # 5. 启动 FastAPI Server
        start_process(
            "FastAPI Server",
            [sys.executable, "-m", "uvicorn", "backend.main:app",
             "--host", "0.0.0.0",
             "--port", "11528"],
            wait_seconds=2
        )

        print("\n" + "="*60)
        print("       所有服务启动完成!")
        print("="*60)
        print("\n服务地址:")
        print("  - FastAPI:   http://localhost:11528")
        print("  - API文档:   http://localhost:11528/docs")
        print("  - ChromaDB:  http://localhost:11530")
        print("\nWorker 分工:")
        print("  - 采集器 Worker: 处理采集任务 (default,collector 队列)")
        print("  - 日报 Worker:   处理日报生成 (report 队列)")
        print("\n按 Ctrl+C 停止所有服务\n")

        # 等待任意进程退出
        while True:
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    print(f"\n[警告] 进程 {proc.pid} 已退出，退出码: {proc.returncode}")
                    cleanup()
                    sys.exit(1)
            time.sleep(1)

    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()
