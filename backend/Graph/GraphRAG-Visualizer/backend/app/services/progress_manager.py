"""
进度管理模块
负责管理文件处理进度的存储和查询
"""
from typing import Dict, Optional
from datetime import datetime
import asyncio


class ProgressManager:
    """进度管理器"""

    def __init__(self):
        # 存储格式: {file_id: {status, progress, message, updated_at}}
        self._progress: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()

    async def set_progress(
        self,
        file_id: str,
        status: str,
        progress: int,
        message: str = "",
        total_blocks: int = 0,
        current_block: int = 0,
        entities_count: int = 0,
        relations_count: int = 0
    ):
        """
        设置文件处理进度

        Args:
            file_id: 文件ID
            status: 状态 (uploading, processing, completed, failed)
            progress: 进度百分比 (0-100)
            message: 进度消息
            total_blocks: 总块数
            current_block: 当前块
            entities_count: 已提取实体数
            relations_count: 已提取关系数
        """
        async with self._lock:
            self._progress[file_id] = {
                "file_id": file_id,
                "status": status,
                "progress": progress,
                "message": message,
                "total_blocks": total_blocks,
                "current_block": current_block,
                "entities_count": entities_count,
                "relations_count": relations_count,
                "updated_at": datetime.now().isoformat()
            }

    async def get_progress(self, file_id: str) -> Optional[Dict]:
        """
        获取文件处理进度

        Args:
            file_id: 文件ID

        Returns:
            进度信息字典,如果不存在返回 None
        """
        async with self._lock:
            return self._progress.get(file_id)

    async def remove_progress(self, file_id: str):
        """
        移除文件处理进度

        Args:
            file_id: 文件ID
        """
        async with self._lock:
            if file_id in self._progress:
                del self._progress[file_id]

    async def clear_old_progress(self, hours: int = 24):
        """
        清理旧的进度记录

        Args:
            hours: 保留最近多少小时的记录
        """
        async with self._lock:
            now = datetime.now()
            to_remove = []

            for file_id, progress in self._progress.items():
                updated_at = datetime.fromisoformat(progress["updated_at"])
                if (now - updated_at).total_seconds() > hours * 3600:
                    to_remove.append(file_id)

            for file_id in to_remove:
                del self._progress[file_id]


# 全局进度管理器实例
progress_manager = ProgressManager()
