#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查看生成的案例内容"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.database.connection import create_session
from backend.database.entities import IPTCCase
from sqlalchemy import desc
import json

def view_latest_case():
    """查看最新生成的案例"""
    with create_session() as session:
        # 查询最新的案例
        case = session.query(IPTCCase).order_by(desc(IPTCCase.created_at)).first()

        if not case:
            print("没有找到案例")
            return

        # 输出案例信息
        output = []
        output.append("=" * 80)
        output.append(f"案例标题: {case.title}")
        output.append("=" * 80)
        output.append(f"\n创建时间: {case.created_at}")
        output.append(f"发布时间: {case.published_at}")

        if case.summary:
            output.append(f"\n案例摘要:\n{case.summary}")

        if case.tags:
            output.append(f"\n标签: {case.tags}")

        if case.related_knowledge_points:
            output.append(f"\n相关知识点:")
            kps = case.related_knowledge_points if isinstance(case.related_knowledge_points, list) else json.loads(case.related_knowledge_points)
            for i, kp in enumerate(kps, 1):
                output.append(f"  {i}. {kp}")

        if case.source_message_ids:
            msg_ids = case.source_message_ids if isinstance(case.source_message_ids, list) else json.loads(case.source_message_ids)
            output.append(f"\n来源消息数量: {len(msg_ids)}")

        if case.source_url:
            output.append(f"\n来源链接: {case.source_url}")

        output.append(f"\n案例内容:\n{'-' * 80}")
        output.append(case.content)
        output.append("-" * 80)

        # 保存到文件
        output_file = project_root / "latest_case.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output))

        print(f"案例已保存到: {output_file}")

        # 同时打印到控制台
        for line in output:
            print(line)

if __name__ == "__main__":
    view_latest_case()
