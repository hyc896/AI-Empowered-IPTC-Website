# -*- coding: utf-8 -*-

"""检查message_platform MySQL数据库中的数据量"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.database.connection import create_session
from backend.database.entities import TongHuaShunMessage, Kr36Message, ArxivMessage

with create_session() as db:
    tonghuashun_count = db.query(TongHuaShunMessage).count()
    kr36_count = db.query(Kr36Message).count()
    arxiv_count = db.query(ArxivMessage).count()

    print("\n=== message_platform MySQL数据统计 ===")
    print(f"同花顺消息: {tonghuashun_count} 条")
    print(f"36氪消息: {kr36_count} 条")
    print(f"arXiv论文: {arxiv_count} 条")
    print(f"总计: {tonghuashun_count + kr36_count + arxiv_count} 条")
    print("=" * 40)
