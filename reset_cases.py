# -*- coding: utf-8 -*-
"""
清空案例数据脚本
删除所有已生成的案例、知识点统计和消息-知识点关联关系
用于重新开始案例生成流程

使用方法：
    python reset_cases.py
"""
import sys
from pathlib import Path

# 添加backend目录到path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(backend_dir))

from backend.database.connection import create_session
from backend.database.entities import (
    IPTCCase,
    IPTCKnowledgePointStats,
    IPTCMessageKnowledgeRelation
)

def reset_cases():
    """清空所有案例相关数据"""
    print("=" * 60)
    print("开始清空案例数据...")
    print("=" * 60)

    try:
        with create_session() as db:
            # 1. 统计当前数据量
            case_count = db.query(IPTCCase).count()
            stats_count = db.query(IPTCKnowledgePointStats).count()
            relation_count = db.query(IPTCMessageKnowledgeRelation).count()

            print(f"\n当前数据统计:")
            print(f"  - 案例数量: {case_count}")
            print(f"  - 知识点统计: {stats_count}")
            print(f"  - 消息-知识点关联: {relation_count}")

            if case_count == 0 and stats_count == 0 and relation_count == 0:
                print("\n✅ 数据库已经是空的，无需清空")
                return

            # 2. 确认删除
            print(f"\n⚠️  警告：即将删除所有案例数据！")
            confirm = input("确认删除？(输入 yes 继续): ")

            if confirm.lower() != 'yes':
                print("❌ 操作已取消")
                return

            # 3. 删除数据
            print("\n开始删除数据...")

            # 删除案例
            deleted_cases = db.query(IPTCCase).delete()
            print(f"  ✓ 删除案例: {deleted_cases} 条")

            # 删除知识点统计
            deleted_stats = db.query(IPTCKnowledgePointStats).delete()
            print(f"  ✓ 删除知识点统计: {deleted_stats} 条")

            # 删除消息-知识点关联
            deleted_relations = db.query(IPTCMessageKnowledgeRelation).delete()
            print(f"  ✓ 删除消息-知识点关联: {deleted_relations} 条")

            # 提交事务
            db.commit()

            print("\n" + "=" * 60)
            print("✅ 案例数据清空完成！")
            print("=" * 60)
            print("\n下一步：运行案例生成脚本")
            print("  python backend/scripts/iptc_auto_scheduler.py --test")
            print("  或")
            print("  python backend/scripts/batch_match_cases.py")

    except Exception as e:
        print(f"\n❌ 清空失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reset_cases()
