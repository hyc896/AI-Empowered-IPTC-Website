# -*- coding: utf-8 -*-

"""
清理arXiv翻译失败的脏数据

修复策略：将summary字段从"[翻译失败，原文] {完整abstract}"
         改为截断的前500字+省略号

Usage:
    python backend/scripts/clean_arxiv_failed_translations.py [--dry-run]

Options:
    --dry-run: 仅统计和预览，不实际修改数据
"""

import sys
import os
from pathlib import Path

# Windows控制台UTF-8编码支持
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.connection import create_session, init_database
from backend.database.entities import ArxivMessage


# 初始化数据库连接
print("初始化数据库连接...")
if not init_database():
    print("❌ 数据库连接失败")
    sys.exit(1)


def clean_failed_translations(dry_run: bool = False):
    """
    清理翻译失败的记录

    Args:
        dry_run: 是否为试运行模式（不实际修改）
    """
    print("=" * 80)
    print("arXiv翻译失败数据清理工具")
    print("=" * 80)

    if dry_run:
        print("\n⚠️  试运行模式：将预览修改但不实际执行")
    else:
        print("\n⚠️  将实际修改数据库记录")

    try:
        with create_session() as db:
            # 查询所有翻译失败的记录
            failed_records = db.query(ArxivMessage).filter(
                ArxivMessage.summary.like('[翻译失败%')
            ).all()

            total_count = len(failed_records)
            print(f"\n✓ 找到 {total_count} 条翻译失败的记录")

            if total_count == 0:
                print("\n✓ 数据库中没有需要清理的记录")
                return

            # 统计信息
            avg_length = sum(len(r.summary) for r in failed_records) / total_count
            max_length = max(len(r.summary) for r in failed_records)
            min_length = min(len(r.summary) for r in failed_records)

            print(f"\n【统计信息】")
            print(f"  平均summary长度: {avg_length:.0f} 字符")
            print(f"  最大长度: {max_length} 字符")
            print(f"  最小长度: {min_length} 字符")

            # 预览前3条
            print(f"\n【预览前3条记录】")
            for i, record in enumerate(failed_records[:3], 1):
                print(f"\n  记录 {i}:")
                print(f"    arXiv ID: {record.arxiv_id}")
                print(f"    标题: {record.title[:60]}...")
                print(f"    当前summary长度: {len(record.summary)} 字符")
                print(f"    前80字符: {record.summary[:80]}...")

            # 开始清理
            if not dry_run:
                print(f"\n【开始清理】")
                updated_count = 0
                for record in failed_records:
                    # 从content（即abstract）中提取前500字
                    new_summary = record.content[:500] + "...[AI翻译暂不可用]"
                    record.summary = new_summary
                    updated_count += 1

                    if updated_count % 20 == 0:
                        print(f"  已处理: {updated_count}/{total_count}")

                db.commit()
                print(f"\n✓ 成功更新 {updated_count} 条记录")
            else:
                print(f"\n【试运行模式】将更新 {total_count} 条记录")
                print(f"\n示例修改:")
                example = failed_records[0]
                new_summary = example.content[:500] + "...[AI翻译暂不可用]"
                print(f"\n  修改前 (长度: {len(example.summary)}):")
                print(f"    {example.summary[:120]}...")
                print(f"\n  修改后 (长度: {len(new_summary)}):")
                print(f"    {new_summary[:120]}...")

                print(f"\n⚠️  若要实际执行，请运行: python backend/scripts/clean_arxiv_failed_translations.py")

    except Exception as e:
        print(f"\n❌ 清理失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 80)


def main():
    """主函数"""
    dry_run = "--dry-run" in sys.argv

    clean_failed_translations(dry_run=dry_run)


if __name__ == "__main__":
    main()
