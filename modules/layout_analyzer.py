"""版面分析模块：检测文字区域和图片区域的坐标。

策略说明
--------
优先使用 PaddleOCR PPStructureV3 进行精确版面分析。
若依赖不满足，自动降级为"整页文字区域"模式：
  - 整页作为一个文字区域送 OCR
  - 不检测独立图片区域（古籍满版文字场景适用）
"""
from __future__ import annotations
import io
from dataclasses import dataclass
from PIL import Image

# PPStructure figure 类型映射
_FIGURE_TYPES = {"figure", "image", "figure_caption", "chart"}
# 过滤面积阈值（像素²），小于此值视为噪点
_MIN_REGION_AREA = 500


@dataclass
class Region:
    region_type: str   # "text" | "image"
    bbox: tuple[int, int, int, int]   # x1, y1, x2, y2 (pixel coords)


def _run_ppstructure(image_bytes: bytes) -> list[dict]:
    """调用 PaddleOCR PPStructureV3 进行版面分析。

    返回格式：[{"type": str, "bbox": [x1,y1,x2,y2]}, ...]
    若 PPStructureV3 不可用，返回空列表（由调用方降级处理）。
    """
    try:
        import numpy as np
        from paddleocr import PPStructureV3

        pipeline = PPStructureV3()
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_np = np.array(img)
        result = pipeline(img_np)

        regions = []
        # PPStructureV3 结果为 StructureResult 对象，遍历其 layout_det_res
        for item in getattr(result, "layout_det_res", []):
            rtype = getattr(item, "label", "text")
            box   = getattr(item, "bbox", None)
            if box is not None and len(box) == 4:
                regions.append({"type": rtype, "bbox": list(map(int, box))})
        return regions

    except Exception:
        # PPStructureV3 不可用，返回空列表触发降级
        return []


def _full_page_region(image_bytes: bytes) -> list[dict]:
    """降级模式：将整页作为一个文字区域返回。"""
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size
    return [{"type": "text", "bbox": [0, 0, w, h]}]


def _ppstructure_to_regions(raw: list[dict]) -> list[Region]:
    """将原始结果转换为 Region 列表，并过滤噪点。"""
    regions: list[Region] = []
    for item in raw:
        x1, y1, x2, y2 = item["bbox"]
        area = abs((x2 - x1) * (y2 - y1))
        if area < _MIN_REGION_AREA:
            continue
        rtype_raw = item.get("type", "text").lower()
        rtype = "image" if rtype_raw in _FIGURE_TYPES else "text"
        regions.append(Region(region_type=rtype, bbox=(x1, y1, x2, y2)))
    return regions


def analyze_layout(image_bytes: bytes) -> list[Region]:
    """对页面图片进行版面分析，返回文字和图片区域列表。

    优先使用 PPStructureV3；不可用时自动降级为整页文字区域模式。
    """
    raw = _run_ppstructure(image_bytes)
    if not raw:
        # 降级：整页作为一个文字区域
        raw = _full_page_region(image_bytes)
    return _ppstructure_to_regions(raw)

