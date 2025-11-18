# -*- coding: utf-8 -*-

"""
消息源配置管理脚本（使用SQLAlchemy ORM）

用途：管理消息源的配置，包括修改RSS feeds、调整采集间隔、启用/禁用等

使用示例：
    # 查看所有消息源
    python backend/scripts/manage_source_config.py list

    # 查看Investing.com配置
    python backend/scripts/manage_source_config.py show investing_com_news

    # 减少Investing.com的RSS源为1个（只保留General News）
    python backend/scripts/manage_source_config.py reduce-feeds investing_com_news

    # 调整采集间隔为5分钟
    python backend/scripts/manage_source_config.py set-interval investing_com_news 300

    # 禁用消息源
    python backend/scripts/manage_source_config.py disable investing_com_news

    # 启用消息源
    python backend/scripts/manage_source_config.py enable investing_com_news
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm.attributes import flag_modified
from backend.database.connection import create_session
from backend.database.entities import MessageSource
from backend.config import ConfigManager


def list_sources():
    """列出所有消息源"""
    with create_session() as db:
        sources = db.query(MessageSource).order_by(MessageSource.name).all()

        print("\n=== 消息源列表 ===\n")
        for source in sources:
            config = source.config or {}
            interval = config.get('interval', 'N/A')
            rss_feeds = config.get('rss_feeds', [])
            status = "启用" if source.is_active else "禁用"

            print(f"名称: {source.name}")
            print(f"  显示名: {source.display_name}")
            print(f"  状态: {status}")
            print(f"  采集间隔: {interval}秒")

            if rss_feeds:
                print(f"  RSS源数量: {len(rss_feeds)}")
                for i, feed in enumerate(rss_feeds, 1):
                    print(f"    [{i}] {feed.get('category', 'N/A')}: {feed.get('url', 'N/A')}")
            else:
                url = config.get('url', 'N/A')
                print(f"  URL: {url}")

            print()


def show_source(source_name: str):
    """显示指定消息源的详细配置"""
    with create_session() as db:
        source = db.query(MessageSource).filter(MessageSource.name == source_name).first()

        if not source:
            print(f"[错误] 消息源 '{source_name}' 不存在")
            return

        print(f"\n=== {source.display_name} 详细配置 ===\n")
        print(f"ID: {source.id}")
        print(f"名称: {source.name}")
        print(f"显示名: {source.display_name}")
        print(f"适配器: {source.adapter_name}")
        print(f"类别: {source.category}")
        print(f"状态: {'启用' if source.is_active else '禁用'}")
        print(f"调度: {source.schedule}")
        print(f"\n配置 (JSON):")
        print(json.dumps(source.config, indent=2, ensure_ascii=False))
        print()


def reduce_feeds(source_name: str):
    """减少Investing.com的RSS源，只保留General News"""
    with create_session() as db:
        source = db.query(MessageSource).filter(MessageSource.name == source_name).first()

        if not source:
            print(f"[错误] 消息源 '{source_name}' 不存在")
            return

        config = source.config or {}
        rss_feeds = config.get('rss_feeds', [])

        if not rss_feeds:
            print(f"[警告] {source_name} 没有配置 rss_feeds")
            return

        print(f"\n当前RSS源数量: {len(rss_feeds)}")
        for i, feed in enumerate(rss_feeds, 1):
            print(f"  [{i}] {feed.get('category', 'N/A')}")

        # 只保留General News
        new_feeds = [
            {
                "url": "https://www.investing.com/rss/news.rss",
                "category": "General News"
            }
        ]

        # 更新配置
        config['rss_feeds'] = new_feeds
        source.config = config
        flag_modified(source, 'config')  # 标记JSON字段已修改
        source.updated_at = datetime.now()

        db.commit()

        print(f"\n[成功] 已将 {source_name} 的RSS源减少为1个（General News）")
        print(f"   更新时间: {source.updated_at}")


def set_interval(source_name: str, interval: int):
    """设置采集间隔"""
    with create_session() as db:
        source = db.query(MessageSource).filter(MessageSource.name == source_name).first()

        if not source:
            print(f"[错误] 消息源 '{source_name}' 不存在")
            return

        config = source.config or {}
        old_interval = config.get('interval', 'N/A')

        # 更新间隔
        config['interval'] = interval
        source.config = config
        flag_modified(source, 'config')  # 标记JSON字段已修改
        source.updated_at = datetime.now()

        db.commit()

        print(f"\n[成功] 已更新 {source_name} 的采集间隔")
        print(f"   旧值: {old_interval}秒")
        print(f"   新值: {interval}秒")
        print(f"   更新时间: {source.updated_at}")


def disable_source(source_name: str):
    """禁用消息源"""
    with create_session() as db:
        source = db.query(MessageSource).filter(MessageSource.name == source_name).first()

        if not source:
            print(f"[错误] 消息源 '{source_name}' 不存在")
            return

        if not source.is_active:
            print(f"[提示] {source_name} 已经是禁用状态")
            return

        source.is_active = False
        source.updated_at = datetime.now()

        db.commit()

        print(f"\n[成功] 已禁用消息源 {source_name}")
        print(f"   更新时间: {source.updated_at}")


def enable_source(source_name: str):
    """启用消息源"""
    with create_session() as db:
        source = db.query(MessageSource).filter(MessageSource.name == source_name).first()

        if not source:
            print(f"[错误] 消息源 '{source_name}' 不存在")
            return

        if source.is_active:
            print(f"[提示] {source_name} 已经是启用状态")
            return

        source.is_active = True
        source.updated_at = datetime.now()

        db.commit()

        print(f"\n[成功] 已启用消息源 {source_name}")
        print(f"   更新时间: {source.updated_at}")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]

    try:
        if command == 'list':
            list_sources()

        elif command == 'show':
            if len(sys.argv) < 3:
                print("[错误] 请提供消息源名称")
                print("用法: python manage_source_config.py show <source_name>")
                return
            show_source(sys.argv[2])

        elif command == 'reduce-feeds':
            if len(sys.argv) < 3:
                print("[错误] 请提供消息源名称")
                print("用法: python manage_source_config.py reduce-feeds <source_name>")
                return
            reduce_feeds(sys.argv[2])

        elif command == 'set-interval':
            if len(sys.argv) < 4:
                print("[错误] 请提供消息源名称和间隔秒数")
                print("用法: python manage_source_config.py set-interval <source_name> <seconds>")
                return
            set_interval(sys.argv[2], int(sys.argv[3]))

        elif command == 'disable':
            if len(sys.argv) < 3:
                print("[错误] 请提供消息源名称")
                print("用法: python manage_source_config.py disable <source_name>")
                return
            disable_source(sys.argv[2])

        elif command == 'enable':
            if len(sys.argv) < 3:
                print("[错误] 请提供消息源名称")
                print("用法: python manage_source_config.py enable <source_name>")
                return
            enable_source(sys.argv[2])

        else:
            print(f"[错误] 未知命令 '{command}'")
            print(__doc__)

    except Exception as e:
        print(f"\n[执行失败] {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
