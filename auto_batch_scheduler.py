#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
批量撞库案例生成调度器
定时检查未处理消息，自动触发撞库和案例生成任务

使用方法：
    python auto_batch_scheduler.py

功能：
    - 启动时立即执行一次检查
    - 之后每1小时自动检查一次
    - 如果有未处理消息，自动执行撞库和案例生成
    - 按Ctrl+C停止
"""

import sys
import time
import schedule
from datetime import datetime
from pathlib import Path

# 添加backend目录到path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from backend.scripts.batch_match_cases import BatchMatchCasesService


def trigger_batch_match():
    """触发批量撞库任务"""
    sys.stdout.reconfigure(encoding='utf-8')

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'\n{"="*60}')
    print(f'[{current_time}] 开始批量撞库任务')
    print(f'{"="*60}')

    try:
        # 创建服务实例并执行
        service = BatchMatchCasesService()
        result = service.run_batch_match()

        # 输出结果
        status = result.get('status')
        if status == 'success':
            print(f'\n✅ 批量撞库任务完成')
            print(f'   - 处理消息: {result.get("total_messages", 0)} 条')
            print(f'   - 匹配关联: {result.get("matched_pairs", 0)} 条')
            print(f'   - 生成案例: {result.get("generated_cases", 0)} 个')
        elif status == 'pending':
            print(f'\n⏳ 等待积攒更多消息')
            print(f'   - 当前消息数: {result.get("total_messages", 0)}')
            print(f'   - 阈值: {result.get("threshold", 0)}')
        else:
            print(f'\n❌ 批量撞库任务失败: {result.get("error", "未知错误")}')

        print(f'\n下次执行时间: 1小时后')
        print(f'{"="*60}\n')

    except Exception as e:
        print(f'❌ 触发批量撞库任务失败: {e}')


def main():
    """主函数"""
    print('='*60)
    print('批量撞库案例生成调度器已启动')
    print('='*60)
    print('配置:')
    print('  - 执行频率: 每1小时')
    print('  - 启动策略: 立即执行一次，然后每1小时执行')
    print('  - 停止方式: 按 Ctrl+C')
    print('='*60)

    # 启动时立即执行一次
    print('\n[启动] 立即执行第一次批量撞库...')
    trigger_batch_match()

    # 设置定时任务：每1小时执行一次
    schedule.every(1).hours.do(trigger_batch_match)

    print('[调度器] 进入定时循环，等待下次执行...\n')

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
