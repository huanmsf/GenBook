"""typst_writer.py — 将 PageData 列表输出为 Typst (.typ) 源文件。

v7：vcol + grid 真竖排方案
---------------------------
原理：
  - 每列文字用 vcol() 函数逐字输出，每字之间插入 linebreak()
  - 使用 #grid(columns: (font_size pt × N), column-gutter: gap) 排列各列
  - 列宽 = 字号（每列只放一个字宽），行距 = 0
  - 列顺序 = 从右到左（第1个 grid cell = 最右列）
  - 空列用 [] 占位，保留原书列节奏

生成的 Typst 结构示例：
  #grid(
    columns: (14pt, 14pt, 14pt, 14pt),
    column-gutter: 6pt,
    // 槽位1（最右）: main  字数=20
    vcol("國立正周易玩辭叙曰大傳曰君子居則觀其象"),
    // 槽位2: main  字数=18
    vcol("子觀其變而玩其占讀易之法盡於此矣易之"),
    // 槽位3: empty
    [],
    // 槽位4: empty
    [],
  )

模板通过 config["guji_layout"]["template"] 选择：
  blank   — 空白模板（港台现代竖版，当前默认）
  classic — 经典古籍（双边框＋鱼尾，后期启用）
"""
from __future__ import annotations
import os
from modules.page_model import PageData, TextColumn


# ---------------------------------------------------------------------------
# utils
# ---------------------------------------------------------------------------

def build_typ_output_path(pdf_path: str) -> str:
    root, _ = os.path.splitext(pdf_path)
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
    '"':  '\\"',
    "[":  "\\[",
    "]":  "\\]",
}


def _escape_typst(text: str) -> str:
    return "".join(_TYPST_ESCAPE.get(ch, ch) for ch in text)


def _px_to_pt(px: float, dpi: int) -> float:
    return px * 72.0 / dpi


def _mm_to_pt(mm: float) -> float:
    return mm * 72.0 / 25.4


def _to_chinese_numeral(num: int) -> str:
    digits = "零一二三四五六七八九"
    if num <= 0:
        return digits[0]
    if num < 10:
        return digits[num]
    if num == 10:
        return "十"
    if num < 20:
        return "十" + digits[num % 10]
    tens, ones = divmod(num, 10)
    return digits[tens] + "十" + (digits[ones] if ones else "")


def _classify_column(col: TextColumn) -> str:
    """简单启发式列类型识别。"""
    if col.column_type != "main":
        return col.column_type
    char_count = len(col.chars)
    if char_count == 0:
        return "empty"
    if char_count <= 6:
        return "title"
    x1, y1, x2, y2 = col.bbox
    col_w = max(1, x2 - x1)
    col_h = max(1, y2 - y1)
    avg_char_h = col_h / max(char_count, 1)
    if col_w < avg_char_h * 0.65:
        return "note"
    return "main"


# ---------------------------------------------------------------------------
# file header — 定义 vcol 函数，设置页面和文字参数
# ---------------------------------------------------------------------------

def _build_header(config: dict) -> str:
    font_family = config.get("font_family", "STKaiTi")
    font_size   = float(config.get("font_size", 12))
    note_size   = float(config.get("note_font_size", 8))
    guji        = config.get("guji_layout", {})
    paper       = guji.get("paper", "jis-b5")
    template    = guji.get("template", "blank")
    tian_tou    = _mm_to_pt(float(guji.get("tian_tou_mm",    25)))
    di_jiao     = _mm_to_pt(float(guji.get("di_jiao_mm",     20)))
    zhuang_ding = _mm_to_pt(float(guji.get("zhuang_ding_mm", 20)))
    shu_kou     = _mm_to_pt(float(guji.get("shu_kou_mm",     15)))
    col_gap     = float(config.get("column_spacing", 6))

    return "\n".join([
        "// GenBook — 自动生成的 Typst 古籍排版文件",
        f"// 模板：{template}  (blank=港台现代竖版 | classic=经典古籍)",
        "// 排版方式：vcol() 逐字竖排 + #grid 多列，列从右到左",
        "// 校对：修改 vcol(\"...\") 括号内文字；空列保留为 []",
        "",
        "#set text(",
        f'  font: ("{font_family}", "Noto Serif CJK TC", "SimSun", "Arial Unicode MS"),',
        f"  size: {font_size:.1f}pt,",
        '  lang: "zh"',
        ")",
        "#set par(leading: 0pt, spacing: 0pt)",
        f"#let _fs = {font_size:.1f}pt         // 正文字号 = 列宽",
        f"#let _ns = {note_size:.1f}pt         // 夹注字号",
        f"#let _gap = {col_gap:.1f}pt          // 列间距",
        f"#set page(",
        f'  paper: "{paper}",',
        f"  margin: (top: {tian_tou:.1f}pt, bottom: {di_jiao:.1f}pt,",
        f"           left: {shu_kou:.1f}pt, right: {zhuang_ding:.1f}pt)",
        ")",
        "",
        "// vcol：将字符串逐字竖排（每字一行）",
        "#let vcol(s, fs: _fs) = {",
        "  set text(size: fs)",
        "  let chars = s.clusters()",
        "  for (i, c) in chars.enumerate() {",
        "    c",
        "    if i < chars.len() - 1 { linebreak() }",
        "  }",
        "}",
        "",
    ])


# ---------------------------------------------------------------------------
# page block
# ---------------------------------------------------------------------------

def _build_page_block(page: PageData, assets_dir: str, page_index: int, config: dict) -> str:
    guji          = config.get("guji_layout", {})
    font_size     = float(config.get("font_size", 12))
    reserve_empty = int(guji.get("reserve_empty_cols", 1))
    template      = guji.get("template", "blank")
    show_page_num  = bool(guji.get("show_page_num", True))
    page_num_style = guji.get("page_num_style", "chinese")
    header_title   = guji.get("header_title", "")
    header_volume  = guji.get("header_volume", "")
    dpi            = page.dpi

    # 列分类与排序（source_order 从右到左）
    cols = sorted(page.text_columns, key=lambda c: c.source_order or 0)
    for idx, col in enumerate(cols, 1):
        if col.source_order == 0:
            col.source_order = idx
        if col.column_type == "main":
            col.column_type = _classify_column(col)

    total_slots = len(cols) + reserve_empty

    lines: list[str] = []

    if page_index > 0:
        lines.append("#pagebreak()")
        lines.append("")

    binding_side = "右→左" if page.page_num % 2 == 1 else "左→右"
    lines.append(
        f"// === 第 {page.page_num} 页  模板={template}"
        f"  {total_slots}槽（OCR {len(cols)}列 + {reserve_empty}空）"
        f"  装订={binding_side} ==="
    )
    lines.append("")

    # 天头
    if header_title or header_volume:
        txt = _escape_typst((header_title + " " + header_volume).strip())
        lines.append(f"#align(center)[{txt}]")
        lines.append("")

    # grid：列宽 = 字号，N 列
    col_w_expr = ", ".join(["_fs"] * total_slots)
    lines.append("#grid(")
    lines.append(f"  columns: ({col_w_expr}),")
    lines.append("  column-gutter: _gap,")
    lines.append("  row-gutter: 0pt,")
    lines.append("  // 列顺序：槽位1=最右列 → 槽位N=最左列")

    for slot_idx in range(total_slots):
        if slot_idx < len(cols):
            col = cols[slot_idx]
            col.slot_index = slot_idx + 1
            text = _escape_typst("".join(c.text for c in col.chars))
            lines.append(
                f"  // 槽位 {slot_idx + 1}: {col.column_type}"
                f"  原列序={col.source_order}  字数={col.expected_char_count}"
            )
            if col.column_type == "note":
                lines.append(f'  vcol("{text}", fs: _ns),')
            elif text.strip():
                lines.append(f'  vcol("{text}"),')
            else:
                lines.append(f"  [],  // 槽位 {slot_idx + 1}: 内容为空")
        else:
            lines.append(f"  // 槽位 {slot_idx + 1}: empty（空列占位）")
            lines.append("  [],")

    lines.append(")")
    lines.append("")

    # 地脚页码
    if show_page_num:
        numeral = (_to_chinese_numeral(page.page_num)
                   if page_num_style == "chinese" else str(page.page_num))
        lines.append(f"#align(center)[{numeral}]")
        lines.append("")

    # 图片（附在页面末尾，后期可调整）
    for img_idx, img_region in enumerate(page.image_regions):
        img_filename = f"p{page.page_num}_img_{img_idx + 1:03d}.png"
        img_path_abs = os.path.join(assets_dir, img_filename)
        os.makedirs(assets_dir, exist_ok=True)
        with open(img_path_abs, "wb") as f:
            f.write(img_region.image_bytes)
        iw_pt = _px_to_pt(img_region.bbox[2] - img_region.bbox[0], dpi)
        ih_pt = _px_to_pt(img_region.bbox[3] - img_region.bbox[1], dpi)
        rel   = os.path.join("assets", img_filename).replace("\\", "/")
        lines.append(f"// 图片 {img_filename}")
        lines.append(f'#image("{rel}", width: {iw_pt:.1f}pt, height: {ih_pt:.1f}pt)')
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main entry
# ---------------------------------------------------------------------------

def create_typst(pages: list[PageData], output_path: str, config: dict) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    assets_dir = os.path.join(os.path.dirname(output_path) or ".", "assets")
    parts = [_build_header(config)]
    for idx, page in enumerate(pages):
        parts.append(_build_page_block(page, assets_dir, idx, config))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
