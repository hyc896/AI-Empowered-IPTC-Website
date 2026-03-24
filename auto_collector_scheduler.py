#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
定时采集调度器
每2小时自动触发一次所有激活的采集器

使用方法：
    python auto_collector_scheduler.py

功能：
    - 启动时立即执行一次采集
    - 之后每2小时自动执行一次
    - 按Ctrl+C停止
"""

import sys
import time
import subprocess
import schedule
from datetime import datetime
from pathlib import Path
from backend.database.connection import create_session
from backend.database.entities import MessageSource
from backend.tasks.collector_tasks import run_collector

SCRIPT_PATH = Path(__file__).parent / 'backend' / 'scripts' / 'batch_match_cases.py'


def run_batch_match():
    """每日执行一次消息匹配与案例生成"""
    sys.stdout.reconfigure(encoding='utf-8')
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'\n{"="*60}')
    print(f'[{current_time}] 开始每日消息匹配与案例生成')
    print(f'{"="*60}')
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            cwd=str(Path(__file__).parent),
            encoding='utf-8',
            errors='replace'
        )
        print(f'[完成] 消息匹配任务结束，返回码: {result.returncode}')
    except Exception as e:
        print(f'❌ 消息匹配任务失败: {e}')


def trigger_all_collectors():
    """触发所有激活的采集器"""
    sys.stdout.reconfigure(encoding='utf-8')

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'\n{"="*60}')
    print(f'[{current_time}] 开始触发采集任务')
    print(f'{"="*60}')

    try:
        with create_session() as db:
            active_sources = db.query(MessageSource).filter(
                MessageSource.is_active == True
            ).all()

            print(f'激活的采集器数量: {len(active_sources)}\n')

            task_ids = []
            for source in active_sources:
                result = run_collector.apply_async(
                    args=(source.name,),
                    queue='collector',
                    priority=5
                )
                print(f'  ✓ {source.name:20s} - 任务ID: {result.id}')
                task_ids.append(result.id)

            print(f'\n所有采集任务已提交到队列')
            print(f'下次执行时间: 2小时后')
            print(f'{"="*60}\n')

    except Exception as e:
        print(f'❌ 触发采集任务失败: {e}')


def main():
    """主函数"""
    print('='*60)
    print('定时采集调度器已启动')
    print('='*60)
    print('配置:')
    print('  - 执行频率: 每2小时')
    print('  - 启动策略: 立即执行一次，然后每2小时执行')
    print('  - 停止方式: 按 Ctrl+C')
    print('='*60)

    # 启动时立即执行一次
    print('\n[启动] 立即执行第一次采集...')
    trigger_all_collectors()

    # 设置定时任务：每2小时采集，每天23:00匹配
    schedule.every(2).hours.do(trigger_all_collectors)
    schedule.every().day.at("23:00").do(run_batch_match)

    print('[调度器] 进入定时循环，等待下次执行...\n')
    print('  - 采集任务: 每2小时')
    print('  - 消息匹配: 每天 23:00\n')

    # 持续运行
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        print('\n\n[停止] 调度器已停止')
        print('='*60)


if __name__ == '__main__':
    main()
