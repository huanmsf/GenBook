"""图片读取模块：将图片文件转为与 PDF 拆页相同的 PageImage 列表。

不修改 pdf_reader.py；PageImage 数据结构复用，便于后续走同一套 OCR/排版。
"""
from __future__ import annotations

import io
import os
from PIL import Image, ImageOps

from modules.pdf_reader import PageImage

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def is_image_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in _IMAGE_EXTS


def collect_image_paths(inputs: list[str]) -> list[str]:
    """收集图片路径：支持单文件、多文件、目录（按文件名排序）。"""
    paths: list[str] = []
    for raw in inputs:
        if not os.path.exists(raw):
            raise FileNotFoundError(f"路径不存在: {raw}")
        if os.path.isdir(raw):
            names = sorted(
                n for n in os.listdir(raw)
                if is_image_file(n) and not n.startswith(".")
            )
            paths.extend(os.path.join(raw, n) for n in names)
        elif is_image_file(raw):
            paths.append(raw)
        else:
            raise ValueError(f"不是支持的图片格式: {raw}")
    if not paths:
        raise ValueError("未找到任何图片文件。")
    return paths


def _load_png_bytes(path: str) -> tuple[bytes, int, int]:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), img.width, img.height


def images_to_pages(
    paths: list[str],
    dpi: int = 300,
    page_start: int | None = None,
    page_end: int | None = None,
) -> list[PageImage]:
    """将图片路径列表转为 PageImage。

    页码按排序后的顺序从 1 起编。dpi 仅用于后续 px→pt 换算（图片本身不再缩放）。
    """
    total = len(paths)
    start_idx = (page_start - 1) if page_start is not None else 0
    end_idx = (page_end - 1) if page_end is not None else total - 1

    if start_idx < 0 or end_idx >= total:
        raise ValueError(
            f"页码范围 {page_start}-{page_end} 超出图片数量 {total}。"
        )
    if start_idx > end_idx:
        raise ValueError(f"起始页 {page_start} 不能大于终止页 {page_end}。")

    results: list[PageImage] = []
    for i in range(start_idx, end_idx + 1):
        png, w, h = _load_png_bytes(paths[i])
        results.append(PageImage(
            page_num=i + 1,
            image_bytes=png,
            orig_width_px=w,
            orig_height_px=h,
            dpi=dpi,
        ))
    return results
