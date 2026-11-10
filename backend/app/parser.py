"""简历文件解析：支持 PDF（PyMuPDF）和纯文本。"""
from fastapi import HTTPException


def extract_text(filename: str, file_bytes: bytes) -> str:
    """按文件类型提取文本内容。"""
    if filename.lower().endswith(".txt"):
        try:
            return file_bytes.decode("utf-8").strip()
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="TXT 文件编码错误，请使用 UTF-8")

    if filename.lower().endswith(".pdf"):
        try:
            import fitz  # PyMuPDF
        except ImportError:  # pragma: no cover
            raise HTTPException(status_code=500, detail="服务器缺少 PyMuPDF，无法解析 PDF")
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text = "\n".join(page.get_text() for page in doc).strip()
            doc.close()
        except Exception:
            raise HTTPException(status_code=400, detail="PDF 解析失败，文件可能已损坏或受密码保护")
        if not text:
            raise HTTPException(
                status_code=400,
                detail="未能从 PDF 中提取到文本（可能是扫描图片版 PDF，暂不支持 OCR）",
            )
        return text

    raise HTTPException(status_code=400, detail="仅支持 .pdf 或 .txt 文件")
