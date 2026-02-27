#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
手动触发所有激活的采集器
使用方法：python trigger_collectors.py
"""

import sys
from backend.database.connection import create_session
from backend.database.entities import MessageSource
from backend.tasks.collector_tasks import run_collector

def main():
    sys.stdout.reconfigure(encoding='utf-8')

    with create_session() as db:
        active_sources = db.query(MessageSource).filter(
            MessageSource.is_active == True
        ).all()

        print(f'开始触发 {len(active_sources)} 个采集器...\n')

        task_ids = []
        for source in active_sources:
            result = run_collector.apply_async(
                args=(source.name,),
                queue='collector',
                priority=5
            )
            print(f'✓ {source.name:20s} - 任务ID: {result.id}')
            task_ids.append(result.id)

        print(f'\n所有采集任务已提交到队列')
        print(f'请查看Worker终端查看执行进度')

if __name__ == '__main__':
    main()
