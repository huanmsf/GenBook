"""OCR 送检图片预处理（新模块，不改 ocr_engine）。

百度高精度接口限制：图片 ≤4MB、最长边 ≤4096px。
高清扫描 PNG 常超限，这里压成 JPEG 后再调用原 recognize_region。
"""
from __future__ import annotations

import io
import logging
from PIL import Image

from modules.ocr_engine import CharResult, recognize_region

log = logging.getLogger(__name__)

_MAX_BYTES = 4_000_000
_MAX_SIDE = 4096


def to_jpeg_payload(image_bytes: bytes) -> tuple[bytes, float]:
    """返回 (jpeg_bytes, scale)。scale 为相对原图缩放比。"""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    orig_w, orig_h = img.size
    scale = 1.0
    longest = max(orig_w, orig_h)
    if longest > _MAX_SIDE:
        scale = _MAX_SIDE / longest
        img = img.resize(
            (max(1, int(orig_w * scale)), max(1, int(orig_h * scale))),
            Image.Resampling.LANCZOS,
        )

    data = b""
    quality = 85
    while quality >= 40:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        data = buf.getvalue()
        if len(data) <= _MAX_BYTES:
            return data, scale
        quality -= 10

    while len(data) > _MAX_BYTES and scale > 0.15:
        scale *= 0.8
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize(
            (max(1, int(orig_w * scale)), max(1, int(orig_h * scale))),
            Image.Resampling.LANCZOS,
        )
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70, optimize=True)
        data = buf.getvalue()
    return data, scale


def recognize_region_safe(
    image_bytes: bytes,
    region_bbox: tuple[int, int, int, int],
    confidence_threshold: float = 0.7,
) -> list[CharResult]:
    """裁剪区域 → 压 JPEG → 调用原 recognize_region，并把坐标还原到整页。"""
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
    if len(image_bytes) > _MAX_BYTES or scale < 1.0:
        log.info(
            f"OCR 送检已压缩: 原图 {len(image_bytes)/1e6:.1f}MB, "
            f"JPEG {len(payload)/1e6:.1f}MB, scale={scale:.3f}"
        )
    return results
