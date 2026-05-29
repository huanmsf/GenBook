"""图片裁剪模块：从页面图片中裁剪出图片区域。"""
from __future__ import annotations
import io
from dataclasses import dataclass
from PIL import Image


@dataclass
class CroppedImage:
    image_bytes: bytes
    bbox: tuple[int, int, int, int]   # 原始像素坐标 x1,y1,x2,y2
    page_num: int


def crop_image_region(
    page_image_bytes: bytes,
    bbox: tuple[int, int, int, int],
    page_num: int,
) -> CroppedImage:
    """从页面图片中裁剪指定区域。

    Args:
        page_image_bytes: 整页 PNG 图片的 bytes。
        bbox: 裁剪区域 (x1, y1, x2, y2)，像素坐标。
        page_num: 所属页码（1-based），记录到结果中。

    Returns:
        CroppedImage，包含裁剪后的 PNG bytes 和元数据。

    Raises:
        ValueError: bbox 超出图片边界。
    """
    img = Image.open(io.BytesIO(page_image_bytes))
    x1, y1, x2, y2 = bbox
    w, h = img.size

    if x1 < 0 or y1 < 0 or x2 > w or y2 > h:
        raise ValueError(
            f"bbox {bbox} 超出图片尺寸 {img.size}。"
        )

    cropped = img.crop((x1, y1, x2, y2))
    buf = io.BytesIO()
    cropped.save(buf, format="PNG")
    return CroppedImage(
        image_bytes=buf.getvalue(),
        bbox=bbox,
        page_num=page_num,
    )
