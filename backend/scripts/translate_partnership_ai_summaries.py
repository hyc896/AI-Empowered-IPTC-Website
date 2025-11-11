# -*- coding: utf-8 -*-

"""
批量翻译Partnership on AI消息摘要
支持双向翻译：英文⇄中文

Usage:
    # 试运行（仅统计，不实际翻译）
    python backend/scripts/translate_partnership_ai_summaries.py --dry-run

    # 英文→中文翻译（默认）
    python backend/scripts/translate_partnership_ai_summaries.py --direction en2zh

    # 中文→英文翻译（测试translator反向能力）
    python backend/scripts/translate_partnership_ai_summaries.py --direction zh2en

    # 限制翻译数量（测试用）
    python backend/scripts/translate_partnership_ai_summaries.py --limit 10

    # 重新翻译所有记录
    python backend/scripts/translate_partnership_ai_summaries.py --retranslate-all
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Windows控制台UTF-8编码支持
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.connection import create_session, init_database
from backend.database.entities import PartnershipAIMessage
from backend.config.config_manager import ConfigManager
from backend.llm.global_llm_manager import GlobalLLMManager


def init_llm_clients():
    """初始化LLM客户端（必须在使用Translator前调用）"""
    print("初始化LLM客户端...")

    try:
        config_path = project_root / "config.yaml"
        config_manager = ConfigManager()
        if not config_manager.load_config(str(config_path)):
            raise Exception("配置加载失败")

        config = config_manager.get_config()
        llm_config = config.get("llm", {})

        llm_manager = GlobalLLMManager.get_instance()
        llm_manager.initialize(
            chat_config=None,
            embedding_config=llm_config.get("embedding", {}),
            fast_config=llm_config.get("fast", {})
        )

        print(f"✓ Fast LLM初始化成功: {llm_config['fast'].get('model')}")
        return True

    except Exception as e:
        print(f"❌ LLM初始化失败: {e}")
        return False


def parse_args():
    """解析命令行参数"""
    import argparse
    parser = argparse.ArgumentParser(description='批量翻译Partnership on AI消息摘要（支持双向翻译）')
    parser.add_argument('--dry-run', action='store_true', help='试运行模式（仅统计，不实际翻译）')
    parser.add_argument('--retranslate-all', action='store_true', help='重新翻译所有记录（默认仅翻译失败的）')
    parser.add_argument('--limit', type=int, default=None, help='限制翻译数量（测试用）')
    parser.add_argument('--batch-size', type=int, default=20, help='批次大小（默认20）')
    parser.add_argument('--direction', type=str, default='en2zh', choices=['en2zh', 'zh2en'],
                        help='翻译方向：en2zh（英文→中文，默认）或 zh2en（中文→英文）')
    return parser.parse_args()


def query_records_to_translate(retranslate_all: bool = False, limit: int = None) -> List[PartnershipAIMessage]:
    """
    查询需要翻译的记录

    Args:
        retranslate_all: 是否重新翻译所有记录
        limit: 限制查询数量

    Returns:
        待翻译的记录列表
    """
    with create_session() as db:
        query = db.query(PartnershipAIMessage)

        if not retranslate_all:
            # 默认只翻译失败的记录
            query = query.filter(
                (PartnershipAIMessage.summary.like('%\\[AI翻译暂不可用\\]%')) |
                (PartnershipAIMessage.summary.like('%\\[AI翻译异常%')) |
                (PartnershipAIMessage.summary.like('%请提供您需要翻译的%')) |
                (PartnershipAIMessage.summary.like('%请提供需要翻译的%')) |
                (PartnershipAIMessage.summary.like('%我将为您翻译%')) |
                (PartnershipAIMessage.summary.like('%我会为您翻译%'))
            )

        # 按发布时间降序排列（优先翻译最新的）
        query = query.order_by(PartnershipAIMessage.published_at.desc())

        if limit:
            query = query.limit(limit)

        records = query.all()
        return records


class ReverseTranslator:
    """
    反向翻译器（中文→英文）
    基于统一translator的扩展
    """
    def __init__(self):
        from backend.llm import get_fast_client
        self.llm_client = get_fast_client()

    def _build_messages_zh2en(self, text: str, context: str = None) -> List[dict]:
        """构建中文→英文翻译消息"""
        system_content = "You are a professional translator specializing in Chinese to English translation. Requirements: accurate, professional terminology, fluent expressions, no explanations or comments."

        if context:
            system_content += f" Content type: {context}."

        user_content = f"Please translate the following Chinese text to English:\n\n{text}"

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]

    async def translate(self, text: str, context: str = None) -> str:
        """
        中文→英文翻译（测试用）

        Args:
            text: 待翻译中文文本
            context: 上下文信息

        Returns:
            翻译后的英文文本
        """
        if not text or not text.strip():
            return text

        try:
            messages = self._build_messages_zh2en(text, context)
            response = await self.llm_client.generate_with_messages_async(
                messages=messages,
                max_tokens=50000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"翻译失败: {e}")
            return text[:500] + "...[Translation Error]"

    async def translate_batch(self, texts: List[str], context: str = None) -> List[str]:
        """批量翻译"""
        tasks = [self.translate(text, context) for text in texts]
        return await asyncio.gather(*tasks)


async def translate_batch(
    records: List[PartnershipAIMessage],
    batch_size: int = 20,
    dry_run: bool = False,
    direction: str = 'en2zh'
) -> Dict[str, Any]:
    """
    批量翻译记录

    Args:
        records: 待翻译的记录列表
        batch_size: 批次大小
        dry_run: 是否为试运行模式
        direction: 翻译方向（en2zh或zh2en）

    Returns:
        统计结果字典
    """
    from backend.llm.translator import get_translator

    total_count = len(records)
    success_count = 0
    failed_count = 0

    direction_text = "英文→中文" if direction == 'en2zh' else "中文→英文"
    print(f"\n开始翻译，共{total_count}条记录")
    print(f"批次大小：{batch_size}")
    print(f"翻译方向：{direction_text}")
    print(f"模式：{'试运行（不实际修改数据库）' if dry_run else '实际翻译'}")
    print("=" * 80)

    if dry_run:
        print("\n⚠️  试运行模式：将模拟翻译但不实际修改数据库")
        return {
            'total': total_count,
            'success': 0,
            'failed': 0
        }

    # 根据翻译方向选择翻译器
    if direction == 'en2zh':
        translator = get_translator()
        context = "AI责任与伦理博客文章"
    else:
        translator = ReverseTranslator()
        context = "AI Responsibility and Ethics Blog Post"

    # 分批处理
    for batch_start in range(0, total_count, batch_size):
        batch_end = min(batch_start + batch_size, total_count)
        batch = records[batch_start:batch_end]
        batch_num = (batch_start // batch_size) + 1
        total_batches = (total_count + batch_size - 1) // batch_size

        print(f"\n【批次 {batch_num}/{total_batches}】处理记录 {batch_start + 1}-{batch_end}/{total_count}", flush=True)

        # 提取待翻译文本
        texts_to_translate = [record.summary for record in batch]
        external_ids = [record.external_id for record in batch]

        try:
            print(f"  翻译中...", flush=True)
            start_time = asyncio.get_event_loop().time()

            translated_texts = await translator.translate_batch(
                texts=texts_to_translate,
                context=context
            )

            elapsed = asyncio.get_event_loop().time() - start_time
            print(f"  翻译完成，耗时: {elapsed:.1f}秒", flush=True)

            # 更新数据库
            print(f"  更新数据库...", flush=True)
            with create_session() as db:
                for i, record in enumerate(batch):
                    translated_text = translated_texts[i]

                    # 检查翻译是否成功
                    import re
                    is_failed = any([
                        '[AI翻译' in translated_text,
                        '请提供您需要翻译的' in translated_text,
                        '请提供需要翻译的' in translated_text,
                        '我将为您翻译' in translated_text,
                        '我会为您翻译' in translated_text,
                        '以下是翻译结果' in translated_text,
                        '原文：' in translated_text and '中文翻译：' in translated_text,
                        bool(re.search(r'\{\{[a-zA-Z_][a-zA-Z0-9_]*\}\}', translated_text)),
                        '[Translation Error]' in translated_text
                    ])

                    if is_failed:
                        failed_count += 1
                        print(f"    ✗ {external_ids[i]}: 翻译失败（降级或幻觉）", flush=True)
                    else:
                        # 更新summary
                        db_record = db.query(PartnershipAIMessage).filter(
                            PartnershipAIMessage.id == record.id
                        ).first()

                        if db_record:
                            db_record.summary = translated_text
                            success_count += 1
                            print(f"    ✓ {external_ids[i][:50]}...: 翻译成功（{len(translated_text)}字）", flush=True)

                db.commit()

        except Exception as e:
            print(f"  ✗ 批次翻译失败: {e}")
            failed_count += len(batch)
            continue

        # 显示进度
        processed = batch_end
        progress = (processed / total_count) * 100
        print(f"  进度: {processed}/{total_count} ({progress:.1f}%)", flush=True)

    return {
        'total': total_count,
        'success': success_count,
        'failed': failed_count
    }


def print_statistics(stats: Dict[str, Any]):
    """
    打印统计结果

    Args:
        stats: 统计结果字典
    """
    print("\n" + "=" * 80)
    print("翻译结果统计")
    print("=" * 80)
    print(f"  总记录数: {stats['total']}")
    if stats['total'] > 0:
        print(f"  成功翻译: {stats['success']} ({stats['success'] / stats['total'] * 100:.1f}%)")
        print(f"  翻译失败: {stats['failed']} ({stats['failed'] / stats['total'] * 100:.1f}%)")
    print("=" * 80)


async def main():
    """主函数"""
    args = parse_args()

    print("=" * 80)
    print("Partnership on AI消息摘要批量翻译工具")
    print("=" * 80)

    # 初始化数据库连接
    print("\n初始化数据库连接...")
    if not init_database():
        print("❌ 数据库连接失败")
        sys.exit(1)
    print("✓ 数据库连接成功")

    # 初始化LLM客户端
    print()
    if not init_llm_clients():
        print("❌ LLM客户端初始化失败")
        sys.exit(1)

    # 查询待翻译记录
    print("\n查询待翻译记录...")
    try:
        records = query_records_to_translate(
            retranslate_all=args.retranslate_all,
            limit=args.limit
        )
        print(f"✓ 找到 {len(records)} 条待翻译记录")

        if len(records) == 0:
            print("\n✓ 没有需要翻译的记录")
            print("\n💡 提示：Partnership on AI的内容默认是英文，使用 --retranslate-all 可翻译所有记录")
            return

        # 显示翻译策略
        if args.retranslate_all:
            print("  翻译策略: 重新翻译所有记录")
        else:
            print("  翻译策略: 仅翻译失败的记录")

        if args.limit:
            print(f"  限制数量: {args.limit} 条")

        print(f"  翻译方向: {'英文→中文' if args.direction == 'en2zh' else '中文→英文'}")

    except Exception as e:
        print(f"❌ 查询失败: {e}")
        sys.exit(1)

    # 确认执行
    if not args.dry_run:
        print(f"\n⚠️  即将翻译 {len(records)} 条记录，此操作将修改数据库")
        confirm = input("是否继续？(y/N): ")
        if confirm.lower() != 'y':
            print("操作已取消")
            return

    # 开始翻译
    start_time = datetime.now()
    stats = await translate_batch(
        records=records,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        direction=args.direction
    )
    end_time = datetime.now()

    # 打印统计结果
    print_statistics(stats)

    elapsed = (end_time - start_time).total_seconds()
    print(f"\n总耗时: {elapsed:.1f}秒")

    if stats['success'] > 0:
        avg_time = elapsed / stats['success']
        print(f"平均翻译速度: {avg_time:.2f}秒/条")


if __name__ == "__main__":
    try:
        # Windows环境需要设置事件循环策略
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
