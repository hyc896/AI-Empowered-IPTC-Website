"""
文件上传路由
处理 PDF 文件上传和文本提取
"""
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse

from app.config import settings
from app.services.pdf_service import PDFService
from app.models.schemas import UploadResponse

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    page_start: int = Query(1, ge=1, description="起始页码"),
    page_end: int = Query(20, ge=1, description="结束页码")
):
    """
    上传 PDF 文件并提取指定页面范围的文本

    Args:
        file: PDF 文件
        page_start: 起始页码（默认 1）
        page_end: 结束页码（默认 20）

    Returns:
        文件信息和提取的文本内容
    """
    # 验证文件类型
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")

    # 生成文件 ID
    file_id = str(uuid.uuid4())

    # 保存文件
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{file_id}.pdf"

    try:
        # 保存上传的文件
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # 提取文本
        text, total_pages = PDFService.extract_text_from_pages(
            str(file_path),
            page_start,
            page_end
        )

        # 调整页面范围
        actual_start, actual_end = PDFService.validate_page_range(
            total_pages, page_start, page_end
        )

        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            total_pages=total_pages,
            current_range=f"{actual_start}-{actual_end}",
            text=text,
            char_count=len(text)
        )

    except Exception as e:
        # 清理文件
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"处理文件失败: {str(e)}")
