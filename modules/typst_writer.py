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
    """生成 Typst 文件的全局设定头部。"""
    font_family  = config.get("font_family", "STKaiTi")
    font_size    = float(config.get("font_size", 14))
    line_spacing = float(config.get("line_spacing", 1.8))
    margin       = config.get("page_margin", {})
    top    = float(margin.get("top",    36))
    bottom = float(margin.get("bottom", 36))
    left   = float(margin.get("left",   36))
    right  = float(margin.get("right",  36))

    lines = [
        "// GenBook — 自动生成的 Typst 古籍排版文件",
        "// 可使用 Typst 编辑器（如 VSCode + Tinymist 插件）打开并预览",
        "// 编译为 PDF：typst compile <此文件> <输出.pdf>",
        "//",
        "",
        f'#set text(font: "{font_family}", size: {font_size:.1f}pt, lang: "zh")',
        f"#set par(leading: {line_spacing:.2f}em, justify: false)",
        f"#set page(",
        f"  margin: (top: {top:.1f}pt, bottom: {bottom:.1f}pt,",
        f"           left: {left:.1f}pt, right: {right:.1f}pt),",
        f")",
        "",
        "// 竖排设定：文字从上到下，列从右到左",
        '#set text(dir: ttb)',
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

    Args:
        page:        单页数据。
        assets_dir:  图片资产保存目录（绝对或相对 .typ 文件的路径）。
        page_index:  页面序号（0-based，用于 pagebreak 判断）。

    Returns:
        该页对应的 Typst 源码字符串。
    """
    lines = []

    # 页分隔（第一页前不加）
    if page_index > 0:
        lines.append("#pagebreak()")
        lines.append("")

    lines.append(f"// --- 第 {page.page_num} 页 ---")
    lines.append("")

    # ── 文字列 ───────────────────────────────────────────────────────────────
    for col in page.text_columns:
        text = "".join(_escape_typst(c.text) for c in col.chars)
        if text.strip():
            lines.append(text)
            lines.append("")

    # ── 图片区域 ─────────────────────────────────────────────────────────────
    for img_idx, img_region in enumerate(page.image_regions):
        img_filename = f"p{page.page_num}_img_{img_idx + 1:03d}.png"
        img_path_abs = os.path.join(assets_dir, img_filename)

        # 保存图片资产
        os.makedirs(assets_dir, exist_ok=True)
        with open(img_path_abs, "wb") as f:
            f.write(img_region.image_bytes)

        # 计算图片宽度（转换为 pt，保持比例）
        x1, y1, x2, y2 = img_region.bbox
        w_pt = _px_to_pt(x2 - x1, page.dpi)

        # 相对于 .typ 文件的路径（assets/ 子目录）
        rel_path = os.path.join("assets", img_filename).replace("\\", "/")
        lines.append(f'#image("{rel_path}", width: {w_pt:.1f}pt)')
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

