# -*- coding: utf-8 -*-

"""
Token Metrics Tracker
统计LLM调用的Token使用情况，帮助监控TPM（Tokens Per Minute）

功能特性：
- 记录每次LLM调用的输入/输出Token数
- 统计最近1分钟的TPM
- 按调用来源分类统计（Translator、FieldEnricher等）
"""

import logging
from datetime import datetime, timedelta
from collections import deque
from typing import Optional, Dict
from threading import Lock

logger = logging.getLogger(__name__)


class TokenMetrics:
    """
    Token使用统计器

    记录每次LLM调用的Token使用情况，并提供TPM统计
    """

    def __init__(self):
        # 记录最近1分钟的调用（用于计算TPM）
        self._recent_calls = deque()  # [(timestamp, tokens, source)]
        self._lock = Lock()

        # 累计统计
        self.total_calls = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0

        # 按来源分类统计
        self.stats_by_source: Dict[str, Dict[str, int]] = {}

    def record(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        source: str = "unknown"
    ):
        """
        记录一次LLM调用

        Args:
            prompt_tokens: 输入Token数
            completion_tokens: 输出Token数
            total_tokens: 总Token数
            source: 调用来源（如"Translator"、"FieldEnricher:region"）
        """
        with self._lock:
            now = datetime.now()

            # 记录到最近调用队列
            self._recent_calls.append((now, total_tokens, source))

            # 清理1分钟以前的记录
            cutoff_time = now - timedelta(minutes=1)
            while self._recent_calls and self._recent_calls[0][0] < cutoff_time:
                self._recent_calls.popleft()

            # 累计统计
            self.total_calls += 1
            self.total_prompt_tokens += prompt_tokens
            self.total_completion_tokens += completion_tokens
            self.total_tokens += total_tokens

            # 按来源统计
            if source not in self.stats_by_source:
                self.stats_by_source[source] = {
                    "calls": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }

            self.stats_by_source[source]["calls"] += 1
            self.stats_by_source[source]["prompt_tokens"] += prompt_tokens
            self.stats_by_source[source]["completion_tokens"] += completion_tokens
            self.stats_by_source[source]["total_tokens"] += total_tokens

            # 计算当前TPM
            current_tpm = sum(tokens for _, tokens, _ in self._recent_calls)

            # 输出到终端（不记录到日志文件）
            print(
                f"【Token】{source} | "
                f"输入: {prompt_tokens:,} | "
                f"输出: {completion_tokens:,} | "
                f"总计: {total_tokens:,} | "
                f"当前TPM: {current_tpm:,}",
                flush=True
            )

            # TPM告警（限制为20000 TPM）
            if current_tpm > 18000:  # 90%阈值
                print(
                    f"\n⚠️  【Token告警】TPM接近限制！\n"
                    f"   当前TPM: {current_tpm:,}/20,000 ({current_tpm/20000*100:.1f}%)\n"
                    f"   来源分布: {self._format_source_distribution()}\n",
                    flush=True
                )

    def _format_source_distribution(self) -> str:
        """
        格式化来源分布信息（最近1分钟）

        Returns:
            来源分布字符串
        """
        # 统计最近1分钟各来源的Token数
        source_tokens = {}
        for _, tokens, source in self._recent_calls:
            source_tokens[source] = source_tokens.get(source, 0) + tokens

        # 按Token数排序
        sorted_sources = sorted(source_tokens.items(), key=lambda x: x[1], reverse=True)

        # 格式化输出
        parts = []
        for source, tokens in sorted_sources[:3]:  # 只显示前3个
            percentage = (tokens / sum(source_tokens.values())) * 100
            parts.append(f"{source}({tokens:,}, {percentage:.1f}%)")

        return ", ".join(parts)

    def get_tpm(self) -> int:
        """
        获取当前TPM（最近1分钟的Token总数）

        Returns:
            当前TPM
        """
        with self._lock:
            now = datetime.now()
            cutoff_time = now - timedelta(minutes=1)

            # 清理过期记录
            while self._recent_calls and self._recent_calls[0][0] < cutoff_time:
                self._recent_calls.popleft()

            return sum(tokens for _, tokens, _ in self._recent_calls)

    def get_stats(self) -> dict:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            return {
                "total_calls": self.total_calls,
                "total_prompt_tokens": self.total_prompt_tokens,
                "total_completion_tokens": self.total_completion_tokens,
                "total_tokens": self.total_tokens,
                "current_tpm": self.get_tpm(),
                "stats_by_source": dict(self.stats_by_source)
            }

    def print_summary(self):
        """打印统计摘要（输出到终端）"""
        stats = self.get_stats()

        print("=" * 60)
        print("【Token统计摘要】")
        print(f"总调用次数: {stats['total_calls']:,}")
        print(f"总输入Token: {stats['total_prompt_tokens']:,}")
        print(f"总输出Token: {stats['total_completion_tokens']:,}")
        print(f"总Token消耗: {stats['total_tokens']:,}")
        print(f"当前TPM: {stats['current_tpm']:,}/20,000 ({stats['current_tpm']/20000*100:.1f}%)")
        print("")
        print("按来源分类统计:")

        for source, source_stats in stats['stats_by_source'].items():
            print(
                f"  {source}: "
                f"{source_stats['calls']}次调用, "
                f"{source_stats['total_tokens']:,} tokens"
            )

        print("=" * 60)
        print("", flush=True)


# 全局单例
_token_metrics_instance: Optional[TokenMetrics] = None


def get_token_metrics() -> TokenMetrics:
    """
    获取全局Token统计实例（单例模式）

    Returns:
        全局Token统计实例
    """
    global _token_metrics_instance
    if _token_metrics_instance is None:
        _token_metrics_instance = TokenMetrics()
        print("【Token统计】初始化完成（TPM限额: 20,000）", flush=True)
    return _token_metrics_instance
