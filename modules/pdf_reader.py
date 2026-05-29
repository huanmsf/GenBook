"""PDF 拆页模块：将 PDF 每页转换为高清图片。"""
from __future__ import annotations
from dataclasses import dataclass
import fitz  # PyMuPDF


@dataclass
class PageImage:
    page_num: int          # 1-based
    image_bytes: bytes     # PNG bytes
    orig_width_px: int     # pixel width at given DPI
    orig_height_px: int    # pixel height at given DPI
    dpi: int


def pdf_to_images(
    pdf_path: str,
    dpi: int = 300,
    page_start: int | None = None,
    page_end: int | None = None,
) -> list[PageImage]:
    """将 PDF 指定页范围转换为高清 PNG 图片列表。

    Args:
        pdf_path:   源 PDF 文件路径。
        dpi:        渲染分辨率，建议 300 以上保证 OCR 质量。
        page_start: 起始页码（1-based，含），None 表示第 1 页。
        page_end:   终止页码（1-based，含），None 表示最后一页。

    Returns:
        PageImage 列表，每页一个元素，page_num 保留原始页码。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 页码范围非法（超出范围或 start > end）。
    """
    import os
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

    doc = fitz.open(pdf_path)
    total = len(doc)

    # 规范化页码（转为 0-based 索引）
    start_idx = (page_start - 1) if page_start is not None else 0
    end_idx   = (page_end - 1)   if page_end   is not None else total - 1

    if start_idx < 0 or end_idx >= total:
        doc.close()
        raise ValueError(
            f"页码范围 {page_start}-{page_end} 超出 PDF 总页数 {total}。"
        )
    if start_idx > end_idx:
        doc.close()
        raise ValueError(
            f"起始页 {page_start} 不能大于终止页 {page_end}。"
        )

    scale  = dpi / 72.0
    matrix = fitz.Matrix(scale, scale)
    results: list[PageImage] = []

    for idx in range(start_idx, end_idx + 1):
        page = doc[idx]
        pix  = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB, alpha=False)
        results.append(PageImage(
            page_num=idx + 1,          # 保留原始 1-based 页码
            image_bytes=pix.tobytes("png"),
            orig_width_px=pix.width,
            orig_height_px=pix.height,
            dpi=dpi,
        ))

    doc.close()
    return results

