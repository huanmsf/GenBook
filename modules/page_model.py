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
    column_type: str = "main"       # main | note | title | empty
    source_order: int = 0           # OCR 原始列序（从右到左）
    slot_index: int = 0             # 模板槽位序号（从右到左）
    expected_char_count: int = 0    # 该列目标字数，默认等于 OCR 识别字数

    def __post_init__(self):
        if self.expected_char_count == 0:
            self.expected_char_count = len(self.chars)


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
