"""
PDF 处理服务
负责 PDF 文件的文本提取和页面管理
"""
import pdfplumber
from pathlib import Path
from typing import Tuple, Optional


class PDFService:
    """PDF 处理服务类"""

    @staticmethod
    def extract_text_from_pages(
        pdf_path: str,
        page_start: int = 1,
        page_end: Optional[int] = None
    ) -> Tuple[str, int]:
        """
        从 PDF 指定页面范围提取文本

        Args:
            pdf_path: PDF 文件路径
            page_start: 起始页码（从 1 开始）
            page_end: 结束页码（包含），None 表示到最后一页

        Returns:
            (提取的文本内容, 总页数)
        """
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

        text_content = []
        total_pages = 0

        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)

            # 调整页码范围
            if page_end is None or page_end > total_pages:
                page_end = total_pages

            if page_start < 1:
                page_start = 1

            if page_start > total_pages:
                raise ValueError(f"起始页码 {page_start} 超出范围（总页数: {total_pages}）")

            # 提取指定范围的文本（pdfplumber 页码从 0 开始）
            for page_num in range(page_start - 1, page_end):
                page = pdf.pages[page_num]
                text = page.extract_text()
                if text:
                    text_content.append(text)

        return "\n\n".join(text_content), total_pages

    @staticmethod
    def get_page_count(pdf_path: str) -> int:
        """
        获取 PDF 总页数

        Args:
            pdf_path: PDF 文件路径

        Returns:
            总页数
        """
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)

    @staticmethod
    def validate_page_range(total_pages: int, page_start: int, page_end: int) -> Tuple[int, int]:
        """
        验证并调整页面范围

        Args:
            total_pages: 总页数
            page_start: 起始页码
            page_end: 结束页码

        Returns:
            (调整后的起始页码, 调整后的结束页码)
        """
        # 确保页码在有效范围内
        page_start = max(1, min(page_start, total_pages))
        page_end = max(page_start, min(page_end, total_pages))

        return page_start, page_end
