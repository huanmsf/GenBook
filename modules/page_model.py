"""结构化数据模型：表示一页处理结果的完整数据。"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class CharData:
    text: str
    bbox: tuple[int, int, int, int]
    confidence: float


@dataclass
class TextColumn:
    bbox: tuple[int, int, int, int]
    chars: list[CharData] = field(default_factory=list)


@dataclass
class ImageRegion:
    bbox: tuple[int, int, int, int]
    image_bytes: bytes


@dataclass
class PageData:
    page_num: int
    orig_width_px: int
    orig_height_px: int
    dpi: int
    text_columns: list[TextColumn] = field(default_factory=list)
    image_regions: list[ImageRegion] = field(default_factory=list)
