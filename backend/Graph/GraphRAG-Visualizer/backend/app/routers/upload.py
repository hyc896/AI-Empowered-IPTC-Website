"""
文件上传路由
处理多种文件格式的上传和文本提取(PDF/Word/EPUB/TXT)
"""
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from app.config import settings
from app.services.pdf_service import PDFService
from app.services.graphrag_service import graphrag_service
from app.services.progress_manager import progress_manager
from app.models.schemas import UploadResponse

# 导入文件处理库
from docx import Document
from ebooklib import epub
from bs4 import BeautifulSoup

router = APIRouter(prefix="/upload", tags=["upload"])


@router.get("/test")
async def test_endpoint():
    """测试端点 - 验证代码是否已重新加载"""
    return {"message": "upload.py 已重新加载", "version": "v2"}


def extract_text_from_docx(file_path: str) -> str:
    """从 Word 文档中提取文本"""
    doc = Document(file_path)
    return '\n'.join([paragraph.text for paragraph in doc.paragraphs])


def extract_text_from_epub(file_path: str) -> str:
    """从 EPUB 文件中提取文本"""
    book = epub.read_epub(file_path)
    text = []
    for item in book.get_items():
        if item.get_type() == 9:  # XHTML
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text.append(soup.get_text())
    return '\n'.join(text)


def extract_text_from_txt(file_path: str) -> str:
    """从 TXT 文件中读取文本"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

async def process_graphrag_async(text: str, file_id: str, filename: str, page_range: str = "全文"):
    """后台异步处理 GraphRAG 实体提取"""
    print(f"🚀 开始后台任务: {filename}, file_id={file_id}, 文本长度={len(text)}, 页码范围={page_range}")

    # 设置初始进度
    await progress_manager.set_progress(
        file_id=file_id,
        status="processing",
        progress=0,
        message="开始处理文件..."
    )

    try:
        if graphrag_service.storage is None:
            print(f"⚙️ 初始化 GraphRAG 服务...")
            await progress_manager.set_progress(
                file_id=file_id,
                status="processing",
                progress=5,
                message="初始化服务..."
            )
            await graphrag_service.initialize(settings.GRAPHRAG_CONFIG_PATH)
            print(f"✅ GraphRAG 服务初始化完成")

        print(f"🔄 调用 process_text...")
        await progress_manager.set_progress(
            file_id=file_id,
            status="processing",
            progress=10,
            message="开始提取实体..."
        )

        # 传递 progress_manager 给 process_text
        await graphrag_service.process_text(text, file_id, filename, page_range, progress_manager)

        print(f"✅ GraphRAG 处理完成: {filename}")
        await progress_manager.set_progress(
            file_id=file_id,
            status="completed",
            progress=100,
            message="处理完成"
        )
    except Exception as e:
        print(f"❌ GraphRAG 处理失败: {filename}, 错误: {str(e)}")
        await progress_manager.set_progress(
            file_id=file_id,
            status="failed",
            progress=0,
            message=f"处理失败: {str(e)}"
        )
        import traceback
        traceback.print_exc()

@router.post("", response_model=UploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    page_start: int = Query(1, ge=1, description="起始页码（仅 PDF）"),
    page_end: int = Query(20, ge=1, description="结束页码（仅 PDF）")
):
    """
    上传文件并提取文本内容
    支持格式：PDF、Word、EPUB、TXT

    Args:
        file: 上传的文件
        page_start: 起始页码（仅 PDF 有效）
        page_end: 结束页码（仅 PDF 有效）

    Returns:
        文件信息和提取的文本内容
    """
    # 获取文件扩展名
    file_ext = os.path.splitext(file.filename)[1].lower()

    # 验证文件类型
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。支持的格式：{', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # 生成文件 ID
    file_id = str(uuid.uuid4())

    # 保存文件
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{file_id}{file_ext}"

    try:
        # 保存上传的文件
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # 根据文件类型提取文本
        total_pages = 1  # 默认页数
        text = ""

        if file_ext == '.pdf':
            text, total_pages = PDFService.extract_text_from_pages(str(file_path))
        elif file_ext in ['.docx', '.doc']:
            text = extract_text_from_docx(str(file_path))
        elif file_ext == '.epub':
            text = extract_text_from_epub(str(file_path))
        elif file_ext == '.txt':
            text = extract_text_from_txt(str(file_path))

        # 计算页码范围
        page_range = f"1-{total_pages}" if file_ext == '.pdf' else "全文"

        # 添加后台任务异步处理 GraphRAG
        print(f"📤 文件上传成功: {file.filename}, 添加后台任务处理, 页码范围: {page_range}")
        background_tasks.add_task(process_graphrag_async, text, file_id, file.filename, page_range)

        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            total_pages=total_pages,
            current_range=f"1-{total_pages}" if file_ext == '.pdf' else "全文",
            text=text,
            char_count=len(text)
        )

    except Exception as e:
        # 清理文件
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"处理文件失败: {str(e)}")


@router.get("/pdf/{file_id}")
async def get_pdf_file(file_id: str):
    """
    获取上传的 PDF 文件

    Args:
        file_id: 文件 ID

    Returns:
        PDF 文件流
    """
    from fastapi.responses import FileResponse

    # 查找文件
    upload_dir = Path(settings.UPLOAD_DIR)
    pdf_files = list(upload_dir.glob(f"{file_id}*.pdf"))

    if not pdf_files:
        raise HTTPException(status_code=404, detail="PDF 文件不存在")

    pdf_path = pdf_files[0]

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name
    )
