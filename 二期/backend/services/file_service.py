# -*- coding: utf-8 -*-

"""
文件上传服务
"""

import os
import uuid
from datetime import datetime
from typing import List
from fastapi import UploadFile, HTTPException, status
from pathlib import Path


class FileService:
    """文件服务类"""

    def __init__(self):
        self.upload_dir = os.getenv("UPLOAD_DIR", "./data/uploads")
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", "104857600"))  # 100MB
        self.allowed_extensions = os.getenv(
            "ALLOWED_EXTENSIONS",
            "jpg,jpeg,png,gif,mp3,mp4,pdf,doc,docx"
        ).split(",")

    async def upload_file(self, file: UploadFile) -> dict:
        """
        上传文件

        Args:
            file: 上传的文件

        Returns:
            文件信息字典

        Raises:
            HTTPException: 文件类型不允许或文件过大
        """
        # 检查文件扩展名
        file_ext = file.filename.split(".")[-1].lower()
        if file_ext not in self.allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {file_ext}"
            )

        # 读取文件内容
        content = await file.read()
        file_size = len(content)

        # 检查文件大小
        if file_size > self.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件过大，最大允许{self.max_file_size / 1024 / 1024}MB"
            )

        # 生成文件名（使用UUID避免重复）
        file_id = str(uuid.uuid4())
        new_filename = f"{file_id}.{file_ext}"

        # 按日期组织目录
        date_path = datetime.now().strftime("%Y/%m")
        save_dir = Path(self.upload_dir) / date_path
        save_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件
        file_path = save_dir / new_filename
        with open(file_path, "wb") as f:
            f.write(content)

        # 返回文件信息
        return {
            "file_id": file_id,
            "filename": file.filename,
            "path": f"/uploads/{date_path}/{new_filename}",
            "size": file_size,
            "type": file.content_type
        }

    async def upload_multiple_files(self, files: List[UploadFile]) -> List[dict]:
        """
        批量上传文件

        Args:
            files: 上传的文件列表

        Returns:
            文件信息列表
        """
        results = []
        for file in files:
            try:
                file_info = await self.upload_file(file)
                results.append(file_info)
            except HTTPException as e:
                # 记录错误但继续处理其他文件
                results.append({
                    "filename": file.filename,
                    "error": e.detail
                })
        return results

    def delete_file(self, file_path: str) -> bool:
        """
        删除文件

        Args:
            file_path: 文件路径

        Returns:
            是否删除成功
        """
        try:
            full_path = Path(self.upload_dir) / file_path.lstrip("/uploads/")
            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception:
            return False
