"""OCR 送检图片预处理（新模块，不改 ocr_engine）。

高精度含位置 accurate()：编码后 ≤10MB、最长边 ≤8192px。
base64 约放大 4/3，原始文件控制在 7.2MB。能原样送 PNG 就不转 JPEG。
"""
from __future__ import annotations

import io
import logging
from PIL import Image

from modules.ocr_engine import CharResult, recognize_region

log = logging.getLogger(__name__)

_MAX_BYTES = 7_200_000
_MAX_SIDE = 8192
_PASSTHROUGH_FMTS = {"JPEG", "JPG", "PNG", "BMP"}


def to_jpeg_payload(image_bytes: bytes) -> tuple[bytes, float]:
    """返回 (送检 bytes, scale)。能过限制时尽量原样；否则先 PNG 再高质量 JPEG。"""
    img = Image.open(io.BytesIO(image_bytes))
    orig_w, orig_h = img.size
    longest = max(orig_w, orig_h)
    fmt = (img.format or "").upper()
    if longest <= _MAX_SIDE and len(image_bytes) <= _MAX_BYTES and fmt in _PASSTHROUGH_FMTS:
        return image_bytes, 1.0

    scale = 1.0
    rgb = img.convert("RGB")
    if longest > _MAX_SIDE:
        scale = _MAX_SIDE / longest
        rgb = rgb.resize(
            (max(1, int(orig_w * scale)), max(1, int(orig_h * scale))),
            Image.Resampling.LANCZOS,
        )

    png_buf = io.BytesIO()
    rgb.save(png_buf, format="PNG")
    png_data = png_buf.getvalue()
    if len(png_data) <= _MAX_BYTES:
        return png_data, scale

    data = b""
    quality = 95
    while quality >= 50:
        buf = io.BytesIO()
        rgb.save(buf, format="JPEG", quality=quality, optimize=True)
        data = buf.getvalue()
        if len(data) <= _MAX_BYTES:
            return data, scale
        quality -= 5

    while len(data) > _MAX_BYTES and scale > 0.15:
        scale *= 0.85
        rgb = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        rgb = rgb.resize(
            (max(1, int(orig_w * scale)), max(1, int(orig_h * scale))),
            Image.Resampling.LANCZOS,
        )
        buf = io.BytesIO()
        rgb.save(buf, format="JPEG", quality=90, optimize=True)
        data = buf.getvalue()
    return data, scale


def recognize_region_safe(
    image_bytes: bytes,
    region_bbox: tuple[int, int, int, int],
    confidence_threshold: float = 0.7,
) -> list[CharResult]:
    """裁剪区域 → 按接口限制送检 → 调用原 recognize_region，并把坐标还原到整页。"""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    x1, y1, x2, y2 = region_bbox
    w, h = img.size
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return []

    crop = img.crop((x1, y1, x2, y2))
    buf = io.BytesIO()
    crop.save(buf, format="PNG")
    payload, scale = to_jpeg_payload(buf.getvalue())
    inv = (1.0 / scale) if scale else 1.0

    local = recognize_region(
        payload,
        region_bbox=(0, 0, 0, 0),
        confidence_threshold=confidence_threshold,
    )

    results: list[CharResult] = []
    for c in local:
        lx1, ly1, lx2, ly2 = c.bbox
        results.append(CharResult(
            text=c.text,
            bbox=(
                int(lx1 * inv) + x1,
                int(ly1 * inv) + y1,
                int(lx2 * inv) + x1,
                int(ly2 * inv) + y1,
            ),
            confidence=c.confidence,
        ))
    if payload is not image_bytes or scale < 1.0:
        kind = "JPEG" if payload[:2] == b"\xff\xd8" else "PNG"
        log.info(
            f"OCR 送检: 原图 {len(image_bytes)/1e6:.1f}MB → "
            f"{kind} {len(payload)/1e6:.1f}MB, scale={scale:.3f}"
        )
    return results
