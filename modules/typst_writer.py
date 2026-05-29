"""typst_writer.py — 将 PageData 列表输出为 Typst (.typ) 源文件。

输出格式 v3：列为单元，兼顾布局还原与可编辑性
------------------------------------------------------
每一竖列输出为一个 #place + #rotate(-90deg) 块：

    // 列  x=381pt  20字  「叙曰大傳…」
    #place(dx: 381.0pt, dy: 207.7pt)[
      #rotate(-90deg, reflow: false)[叙曰大傳曰君子居則觀其象而玩其辭]
    ]

优势：
  - 文件大小：每列 4行（而非每字1行），缩小 10-20倍
  - 布局还原：每列 X/Y 坐标与原 PDF 精确对应
  - 可编辑：直接修改方括号内的文字即可校对
  - 可区分：注释列（字数少）vs 正文列（字数多）清晰可辨

使用方式
--------
    from modules.typst_writer import create_typst
    create_typst(all_pages, "output/book.typ", config)

编译为 PDF（需安装 typst CLI）：
    typst compile output/book.typ output/book.pdf
"""
from __future__ import annotations
import os
from modules.page_model import PageData, TextColumn


# ---------------------------------------------------------------------------
# 公共工具函数
# ---------------------------------------------------------------------------

def build_typ_output_path(pdf_path: str) -> str:
    """将 PDF 路径转换为对应的 .typ 路径（只替换扩展名）。"""
    root, ext = os.path.splitext(pdf_path)
    return root + ".typ"


_TYPST_ESCAPE: dict[str, str] = {
    "\\": "\\\\",
    "#":  "\\#",
    "@":  "\\@",
    "<":  "\\<",
    ">":  "\\>",
    "_":  "\\_",
    "*":  "\\*",
    "`":  "\\`",
    "$":  "\\$",
    "=":  "\\=",
    "~":  "\\~",
    "'":  "\\'",
    "\"": "\\\"",
    "[":  "\\[",
    "]":  "\\]",
}


def _escape_typst(text: str) -> str:
    """转义 Typst 源码中的特殊字符。"""
    return "".join(_TYPST_ESCAPE.get(ch, ch) for ch in text)


def _px_to_pt(px: float, dpi: int) -> float:
    """像素坐标转换为排版点（pt）。"""
    return px * 72.0 / dpi


# ---------------------------------------------------------------------------
# 文件头
# ---------------------------------------------------------------------------

def _build_header(config: dict) -> str:
    """生成 Typst 文件全局排版设定头部。"""
    font_family = config.get("font_family", "STKaiTi")
    font_size   = float(config.get("font_size", 14))
    margin      = config.get("page_margin", {})
    top    = float(margin.get("top",    36))
    bottom = float(margin.get("bottom", 36))
    left   = float(margin.get("left",   36))
    right  = float(margin.get("right",  36))

    return "\n".join([
        "// GenBook — 自动生成的 Typst 古籍排版文件",
        "// 排版方式：每竖列整体定位（#place），列内文字竖排（#rotate(-90deg)）",
        "//",
        "// 编辑说明：",
        "//   · 校对文字：直接修改 #rotate(-90deg)[ ... ] 方括号内的内容",
        "//   · 调整列位置：修改 #place(dx:..., dy:...) 的坐标值",
        "//   · 调整字体/字号：修改文件开头的 #set text(...)",
        "//",
        "// 编译为 PDF：typst compile <此文件>",
        "// 实时预览：VSCode 安装 Tinymist 插件后自动预览",
        "",
        "#set text(",
        f'  font: ("{font_family}", "Noto Serif CJK TC", "SimSun", "Arial Unicode MS"),',
        f"  size: {font_size:.1f}pt,",
        '  lang: "zh"',
        ")",
        "#set page(margin: (",
        f"  top: {top:.1f}pt, bottom: {bottom:.1f}pt,",
        f"  left: {left:.1f}pt, right: {right:.1f}pt",
        "))",
        "",
    ])


# ---------------------------------------------------------------------------
# 单页内容
# ---------------------------------------------------------------------------

def _col_label(col: TextColumn, dpi: int) -> str:
    """生成列注释标签，便于人工识别内容。"""
    char_count = len(col.chars)
    preview = "".join(c.text for c in col.chars[:4] if c.text.strip())
    x1, y1, x2, y2 = col.bbox
    x_pt = _px_to_pt((x1 + x2) / 2, dpi)
    label = f"x={x_pt:.0f}pt  {char_count}字"
    if preview:
        label += f"  [{preview}...]"
    return label


def _build_page_block(
    page: PageData,
    assets_dir: str,
    page_index: int,
) -> str:
    """将单页 PageData 转换为 Typst 源码（v3：列为单元）。"""
    dpi = page.dpi
    pw  = _px_to_pt(page.orig_width_px,  dpi)
    ph  = _px_to_pt(page.orig_height_px, dpi)

    lines: list[str] = []

    if page_index > 0:
        lines.append("#pagebreak()")
        lines.append("")

    col_count = len(page.text_columns)
    img_count = len(page.image_regions)
    lines.append(f"// === 第 {page.page_num} 页  ({pw:.0f}pt x {ph:.0f}pt  {col_count}列 {img_count}图) ===")
    lines.append("")
    lines.append(f"#block(width: {pw:.0f}pt, height: {ph:.0f}pt, clip: false)[")
    lines.append("")

    for col in page.text_columns:
        if not col.chars:
            continue
        x1, y1, x2, y2 = col.bbox
        col_x = _px_to_pt((x1 + x2) / 2, dpi)
        col_y = _px_to_pt(y1, dpi)
        text  = _escape_typst("".join(c.text for c in col.chars))
        if not text.strip():
            continue
        label = _col_label(col, dpi)
        lines.append(f"  // {label}")
        lines.append(f"  #place(dx: {col_x:.1f}pt, dy: {col_y:.1f}pt)[")
        lines.append(f"    #rotate(-90deg, reflow: false)[{text}]")
        lines.append(f"  ]")
        lines.append("")

    for img_idx, img_region in enumerate(page.image_regions):
        img_filename = f"p{page.page_num}_img_{img_idx + 1:03d}.png"
        img_path_abs = os.path.join(assets_dir, img_filename)
        os.makedirs(assets_dir, exist_ok=True)
        with open(img_path_abs, "wb") as f:
            f.write(img_region.image_bytes)
        ix1, iy1, ix2, iy2 = img_region.bbox
        ix_pt = _px_to_pt(ix1, dpi)
        iy_pt = _px_to_pt(iy1, dpi)
        iw_pt = _px_to_pt(ix2 - ix1, dpi)
        ih_pt = _px_to_pt(iy2 - iy1, dpi)
        rel_path = os.path.join("assets", img_filename).replace("\\", "/")
        lines.append(f"  // image  x={ix_pt:.0f}pt y={iy_pt:.0f}pt  {iw_pt:.0f}x{ih_pt:.0f}pt")
        lines.append(
            f"  #place(dx: {ix_pt:.1f}pt, dy: {iy_pt:.1f}pt)"
            f'[#image("{rel_path}", width: {iw_pt:.1f}pt, height: {ih_pt:.1f}pt)]'
        )
        lines.append("")

    lines.append("]")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def create_typst(
    pages: list[PageData],
    output_path: str,
    config: dict,
) -> None:
    """将 PageData 列表写出为 Typst (.typ) 源文件。"""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    assets_dir = os.path.join(os.path.dirname(output_path) or ".", "assets")
    parts = [_build_header(config)]
    for idx, page in enumerate(pages):
        parts.append(_build_page_block(page, assets_dir, idx))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
