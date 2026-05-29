"""typst_writer.py — 将 PageData 列表输出为 Typst (.typ) 源文件。

生成的 .typ 文件结构
--------------------
- 文件头：#set text / #set page 等全局排版设定
- 每页：// --- 第 N 页 --- 注释 + 正文字符串 + 图片引用
- 图片资产：保存至 <typ文件同目录>/assets/p<N>_img_<i>.png

使用方式
--------
    from modules.typst_writer import create_typst
    create_typst(all_pages, "output/book.typ", config)

编译为 PDF（需安装 typst CLI）：
    typst compile output/book.typ output/book.pdf
"""
from __future__ import annotations
import os
from modules.page_model import PageData


# ---------------------------------------------------------------------------
# 公共工具函数
# ---------------------------------------------------------------------------

def build_typ_output_path(pdf_path: str) -> str:
    """将 PDF 路径转换为对应的 .typ 路径（只替换扩展名）。

    Examples:
        "output/book_out_20260101.pdf" → "output/book_out_20260101.typ"
        "output/result"               → "output/result.typ"
    """
    root, ext = os.path.splitext(pdf_path)
    return root + ".typ"


# Typst 需要转义的特殊字符
_TYPST_ESCAPE = {
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
    """转义 Typst 源码中的特殊字符，防止 CJK 内容被误解析。"""
    result = []
    for ch in text:
        result.append(_TYPST_ESCAPE.get(ch, ch))
    return "".join(result)


def _px_to_pt(px: float, dpi: int) -> float:
    """像素坐标转换为排版点（pt），1pt = 1/72 英寸。"""
    return px * 72.0 / dpi


# ---------------------------------------------------------------------------
# 文件头生成
# ---------------------------------------------------------------------------

def _build_header(config: dict) -> str:
    """生成 Typst 文件的全局设定头部。

    排版策略：使用 #place(dx, dy) 绝对坐标定位每个字符，
    完全忠实 OCR 原始位置，不依赖任何竖排语法（Typst 不支持 dir:ttb）。
    每页使用 #block(width, height)[ ... ] 包裹，确保页面尺寸正确。
    """
    font_family = config.get("font_family", "STKaiTi")
    font_size   = float(config.get("font_size", 14))
    margin      = config.get("page_margin", {})
    top    = float(margin.get("top",    36))
    bottom = float(margin.get("bottom", 36))
    left   = float(margin.get("left",   36))
    right  = float(margin.get("right",  36))

    lines = [
        "// GenBook — 自动生成的 Typst 古籍排版文件",
        "// 排版方式：每字按 OCR 坐标绝对定位（#place），忠实还原原始版面",
        "// 使用 VSCode + Tinymist 插件打开可实时预览",
        "// 编译为 PDF：typst compile <此文件> <输出.pdf>",
        "// 注意：若预览显示方块字，请将字体文件放入系统字体目录后重启 VSCode",
        "//",
        "",
        f'#set text(font: ("{font_family}", "Noto Serif CJK TC", "SimSun", "Arial Unicode MS"),',
        f'          size: {font_size:.1f}pt, lang: "zh")',
        "#set page(margin: (top: " + f"{top:.1f}pt, bottom: {bottom:.1f}pt, "
        + f"left: {left:.1f}pt, right: {right:.1f}pt))",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 单页内容生成
# ---------------------------------------------------------------------------

def _build_page_block(
    page: PageData,
    assets_dir: str,
    page_index: int,
) -> str:
    """将单个 PageData 转换为 Typst 页面块字符串。

    策略：每个字符用 #place(dx:Xpt, dy:Ypt)[字] 绝对定位，
    完全忠实 OCR 原始坐标，不依赖竖排语法。
    整页用 #block(width, height, clip:true)[ ... ] 包裹确保尺寸。
    """
    dpi  = page.dpi
    pw   = _px_to_pt(page.orig_width_px,  dpi)
    ph   = _px_to_pt(page.orig_height_px, dpi)

    lines = []

    # 页分隔（第一页前不加）
    if page_index > 0:
        lines.append("#pagebreak()")
        lines.append("")

    lines.append(f"// --- 第 {page.page_num} 页 (原始尺寸 {pw:.1f}pt × {ph:.1f}pt) ---")
    lines.append("")

    # 用 #block 包裹整页，设置与原始页面相同的宽高
    lines.append(f"#block(width: {pw:.1f}pt, height: {ph:.1f}pt, clip: false)[")
    lines.append("")

    # ── 文字列：每字绝对定位 ──────────────────────────────────────────────────
    for col in page.text_columns:
        for char in col.chars:
            x1, y1, x2, y2 = char.bbox
            # bbox 中心点 → pt 坐标
            cx_pt = _px_to_pt((x1 + x2) / 2, dpi)
            cy_pt = _px_to_pt((y1 + y2) / 2, dpi)
            ch_size_pt = _px_to_pt(y2 - y1, dpi)  # 字符高度用于 font-size 参考
            ch = _escape_typst(char.text)
            if not ch.strip():
                continue
            # #place(dx, dy) 相对页面左上角定位
            lines.append(
                f'  #place(dx: {cx_pt:.1f}pt, dy: {cy_pt:.1f}pt)[{ch}]'
            )

    lines.append("")

    # ── 图片区域：绝对定位嵌入 ────────────────────────────────────────────────
    for img_idx, img_region in enumerate(page.image_regions):
        img_filename = f"p{page.page_num}_img_{img_idx + 1:03d}.png"
        img_path_abs = os.path.join(assets_dir, img_filename)

        os.makedirs(assets_dir, exist_ok=True)
        with open(img_path_abs, "wb") as f:
            f.write(img_region.image_bytes)

        x1, y1, x2, y2 = img_region.bbox
        x_pt  = _px_to_pt(x1, dpi)
        y_pt  = _px_to_pt(y1, dpi)
        w_pt  = _px_to_pt(x2 - x1, dpi)
        h_pt  = _px_to_pt(y2 - y1, dpi)
        rel_path = os.path.join("assets", img_filename).replace("\\", "/")
        lines.append(
            f'  #place(dx: {x_pt:.1f}pt, dy: {y_pt:.1f}pt)['
            f'#image("{rel_path}", width: {w_pt:.1f}pt, height: {h_pt:.1f}pt)]'
        )

    lines.append("]")  # 关闭 #block
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
    """将 PageData 列表写出为 Typst (.typ) 源文件。

    图片资产保存在 <output_path同目录>/assets/ 下。

    Args:
        pages:       所有页的结构化数据。
        output_path: 输出 .typ 文件路径。
        config:      排版配置字典（来自 layout_config.yaml）。
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # 图片资产目录与 .typ 文件同级
    assets_dir = os.path.join(os.path.dirname(output_path) or ".", "assets")

    parts = [_build_header(config)]

    for idx, page in enumerate(pages):
        parts.append(_build_page_block(page, assets_dir, idx))

    typ_source = "\n".join(parts)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(typ_source)

