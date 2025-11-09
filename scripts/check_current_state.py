# -*- coding: utf-8 -*-

"""
检查message_platform当前状态
- 数据库配置中的chroma_collection值
- MySQL各表的记录数
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.database.connection import create_session
from backend.database.entities import MessageSource, TongHuaShunMessage, Kr36Message, ArxivMessage

def check_current_state():
    """检查当前状态"""

    print("\n" + "=" * 80)
    print("MESSAGE PLATFORM - 当前状态检查")
    print("=" * 80)

    with create_session() as db:
        # 1. 检查消息源配置
        print("\n【1. 数据库配置】")
        sources = db.query(MessageSource).filter(MessageSource.is_active == True).all()

        print(f"\n找到 {len(sources)} 个激活的消息源：")
        print("-" * 80)

        for source in sources:
            config = source.config or {}
            chroma_collection = config.get('chroma_collection', '[未配置]')
            mysql_table = config.get('mysql_table', '[未配置]')

            print(f"\n消息源: {source.display_name} ({source.name})")
            print(f"  MySQL表: {mysql_table}")
            print(f"  ChromaDB Collection: {chroma_collection}")

        # 2. 检查MySQL记录数
        print("\n" + "-" * 80)
        print("\n【2. MySQL数据统计】\n")

        try:
            tonghuashun_count = db.query(TongHuaShunMessage).count()
            print(f"同花顺消息 (mp_tonghuashun_messages): {tonghuashun_count} 条")
        except Exception as e:
            print(f"同花顺消息表查询失败: {e}")
            tonghuashun_count = 0

        try:
            kr36_count = db.query(Kr36Message).count()
            print(f"36氪消息 (mp_kr36_messages): {kr36_count} 条")
        except Exception as e:
            print(f"36氪消息表查询失败: {e}")
            kr36_count = 0

        try:
            arxiv_count = db.query(ArxivMessage).count()
            print(f"arXiv论文 (mp_arxiv_messages): {arxiv_count} 条")
        except Exception as e:
            print(f"arXiv论文表查询失败: {e}")
            arxiv_count = 0

        total = tonghuashun_count + kr36_count + arxiv_count
        print(f"\nMySQL总计: {total} 条记录")

    print("\n" + "=" * 80)
    print("检查完成")
    print("=" * 80 + "\n")

if __name__ == '__main__':
    check_current_state()
