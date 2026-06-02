"""OCR 结果缓存：序列化/反序列化 list[PageData] 为 JSON。

格式说明：
  每个 PageData 序列化为一个 JSON 对象，image_bytes 用 base64 编码。
  文件整体是一个 JSON 数组，扩展名 .ocr.json。

用法：
    from modules.ocr_cache import save_ocr_cache, load_ocr_cache, cache_path_for
    # 保存
    cache = cache_path_for(output_pdf)    # e.g. output/zywc_out_xxx.ocr.json
    save_ocr_cache(all_pages, cache)
    # 读取并重新生成
    all_pages = load_ocr_cache(cache)
"""
from __future__ import annotations
import base64, json, os
from modules.page_model import PageData, TextColumn, CharData, ImageRegion


# ── 序列化 ──────────────────────────────────────────────────────────────────

def _char_to_dict(c: CharData) -> dict:
    return {"text": c.text, "bbox": list(c.bbox), "confidence": c.confidence}


def _col_to_dict(col: TextColumn) -> dict:
    return {
        "bbox": list(col.bbox),
        "chars": [_char_to_dict(c) for c in col.chars],
        "column_type": col.column_type,
        "source_order": col.source_order,
        "slot_index": col.slot_index,
        "expected_char_count": col.expected_char_count,
    }


def _img_to_dict(ir: ImageRegion) -> dict:
    return {
        "bbox": list(ir.bbox),
        "image_b64": base64.b64encode(ir.image_bytes).decode("ascii"),
    }


def _page_to_dict(page: PageData) -> dict:
    return {
        "page_num": page.page_num,
        "orig_width_px": page.orig_width_px,
        "orig_height_px": page.orig_height_px,
        "dpi": page.dpi,
        "text_columns": [_col_to_dict(c) for c in page.text_columns],
        "image_regions": [_img_to_dict(ir) for ir in page.image_regions],
    }


def save_ocr_cache(pages: list[PageData], path: str) -> None:
    """将 OCR 结果序列化为 JSON 文件。"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    data = [_page_to_dict(p) for p in pages]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 反序列化 ─────────────────────────────────────────────────────────────────

def _dict_to_char(d: dict) -> CharData:
    return CharData(text=d["text"], bbox=tuple(d["bbox"]), confidence=d["confidence"])


def _dict_to_col(d: dict) -> TextColumn:
    col = TextColumn(
        bbox=tuple(d["bbox"]),
        chars=[_dict_to_char(c) for c in d["chars"]],
        column_type=d.get("column_type", "main"),
        source_order=d.get("source_order", 0),
        slot_index=d.get("slot_index", 0),
        expected_char_count=d.get("expected_char_count", 0),
    )
    return col


def _dict_to_img(d: dict) -> ImageRegion:
    return ImageRegion(
        bbox=tuple(d["bbox"]),
        image_bytes=base64.b64decode(d["image_b64"]),
    )


def _dict_to_page(d: dict) -> PageData:
    return PageData(
        page_num=d["page_num"],
        orig_width_px=d["orig_width_px"],
        orig_height_px=d["orig_height_px"],
        dpi=d["dpi"],
        text_columns=[_dict_to_col(c) for c in d.get("text_columns", [])],
        image_regions=[_dict_to_img(ir) for ir in d.get("image_regions", [])],
    )


def load_ocr_cache(path: str) -> list[PageData]:
    """从 .ocr.json 缓存文件恢复 PageData 列表。"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [_dict_to_page(d) for d in data]


def cache_path_for(output_pdf: str) -> str:
    """根据输出 PDF 路径生成对应的 .ocr.json 缓存路径。
    例：output/zywc_out_20260602153139.pdf
      → output/zywc_out_20260602153139.ocr.json
    """
    base = os.path.splitext(output_pdf)[0]
    return base + ".ocr.json"
