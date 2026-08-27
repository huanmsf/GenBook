"""typst_horizontal_writer.py — 简体横排（新模块，不改 typst_flow_writer / typst_writer）。

两种模式（与竖版 --flow / --no-flow 对应）：
- flow=False（默认）：按 OCR JSON 坐标等比换算绝对定位
  高度相近的字在同一行（原图第 n 行 → PDF 第 n 行），行内左→右
- flow=True：将竖排列重排为横排段落（两端对齐、首行缩进）

公开 API：
    create_typst(pages, output_path, config, flow=False)
"""
from __future__ import annotations

import os
from modules.page_model import PageData, CharData
from modules.typst_flow_writer import (
    _esc,
    _mm_to_pt,
    _px_to_pt,
    _recluster_chars,
    _to_chinese_numeral,
)

_TYPST_NAMED_PAPER = {
    "jis-b5", "jis-b4", "a4", "a5", "iso-b5", "us-letter", "us-legal", "letter", "b5",
}

_PAPER_PT: dict[str, tuple[float, float]] = {
    "jis-b5": (515.91, 728.50),
    "jis-b4": (728.50, 1031.81),
    "a4":     (595.28, 841.89),
    "a5":     (419.53, 595.28),
    "letter": (612.00, 792.00),
    "b5":     (498.90, 708.66),
    "d32kai": (396.85, 575.43),
}

_BANNER_ABS = """\
// ╔══════════════════════════════════════════════════════════════════╗
// ║  GenBook 简体横排 · 绝对坐标  (typst_horizontal_writer.py)       ║
// ║                                                                  ║
// ║  按 OCR JSON 坐标等比换算：高度相近=同行，行内左→右 #place      ║
// ║  dx = x/页宽×版心宽，dy = y/页高×版心高（原图第 n 行→PDF 第 n 行）║
// ║  编辑：改 dx/dy 即可挪词；改 hrow 字符串即可改字                 ║
// ╚══════════════════════════════════════════════════════════════════╝"""

_BANNER_FLOW = """\
// ╔══════════════════════════════════════════════════════════════════╗
// ║  GenBook 简体横排 · 流式段落  (typst_horizontal_writer.py)       ║
// ║                                                                  ║
// ║  竖排 OCR 列按阅读序（右→左）重排为横排段落                      ║
// ║  正文两端对齐，首行缩进两字（大陆出版习惯）                      ║
// ╚══════════════════════════════════════════════════════════════════╝"""


def _paper_dims_pt(g: dict) -> tuple[float, float]:
    w_mm, h_mm = g.get("page_width_mm"), g.get("page_height_mm")
    if w_mm and h_mm:
        return _mm_to_pt(float(w_mm)), _mm_to_pt(float(h_mm))
    paper = str(g.get("paper", "jis-b5")).lower()
    return _PAPER_PT.get(paper, (515.91, 728.50))


def _page_size_line(g: dict) -> str:
    paper = str(g.get("paper", "jis-b5"))
    w_mm, h_mm = g.get("page_width_mm"), g.get("page_height_mm")
    if paper.lower() not in _TYPST_NAMED_PAPER and w_mm and h_mm:
        return f"  width: {float(w_mm):.0f}mm, height: {float(h_mm):.0f}mm,"
    return f'  paper: "{paper}",'


def _build_header(config: dict, flow: bool = False) -> str:
    ff = config.get("font_family", "STKaiTi")
    fs = float(config.get("font_size", 12))
    _ls_raw = float(config.get("line_spacing", 0))
    g = config.get("guji_layout", {})
    paper = g.get("paper", "jis-b5")
    tmpl = g.get("template", "blank")
    st = g.get("styles", {})
    indent_em = float(g.get("first_line_indent_em", 2))
    leading = _ls_raw if _ls_raw > 0 else round(fs * 0.65, 2)
    ls_abs = _ls_raw if _ls_raw > 0 else round(fs * 0.20, 2)
    mode_tag = "横排流式段落" if flow else "横排绝对坐标"

    tian_tou = _mm_to_pt(float(g.get("tian_tou_mm", 22)))
    di_jiao = _mm_to_pt(float(g.get("di_jiao_mm", 20)))
    zhuang_ding = _mm_to_pt(float(g.get("zhuang_ding_mm", 22)))
    shu_kou = _mm_to_pt(float(g.get("shu_kou_mm", 16)))

    def _fw(key: str, default: float) -> float:
        return round(fs * float(st.get(key, default)), 2)

    heading_fw = _fw("heading_scale", 1.50)
    title_fw = _fw("title_scale", 1.30)
    subtitle_fw = _fw("subtitle_scale", 1.00)
    author_fw = _fw("author_scale", 0.80)
    interp_fw = _fw("interp_scale", 0.80)
    note_fw = _fw("note_scale", 0.54)
    pagenum_fw = _fw("pagenum_scale", 0.70)
    cs_r_val = round((leading if flow else ls_abs) / fs, 4) if fs else 0.65

    if flow:
        par_line = (
            f"#set par(leading: {leading:.2f}pt, spacing: {leading:.2f}pt, "
            f"justify: true, first-line-indent: {indent_em:.0f}em)"
        )
        extras = [
            "#let htitle(s)  = align(center)[#text(size: title_fw)[#s]]",
            "#let hheading(s)= align(center)[#text(size: heading_fw)[#s]]",
            "#let hnote(s)   = text(size: note_fw)[#s]",
        ]
        banner = _BANNER_FLOW
    else:
        par_line = "#set par(leading: 0pt, spacing: 0pt)"
        extras = [
            "// ── 横排行函数（对应竖版 vcol）────────────────────────",
            "#let hrow(s, fw: cw) = text(size: fw)[#s]",
            "#let htitle(s)  = hrow(s, fw: title_fw)",
            "#let hheading(s)= hrow(s, fw: heading_fw)",
            "#let hnote(s)   = hrow(s, fw: note_fw)",
        ]
        banner = _BANNER_ABS

    rows = [
        banner,
        "",
        f"// 模板：{tmpl}  正文:{fs}pt  纸张:{paper}  模式:{mode_tag}",
        "",
        "#set page(",
        _page_size_line(g),
        f"  margin: (top: {tian_tou:.1f}pt, bottom: {di_jiao:.1f}pt,",
        f"           left: {zhuang_ding:.1f}pt, right: {shu_kou:.1f}pt)",
        ")",
        "#set text(",
        f'  font: ("{ff}", "Songti SC", "Noto Serif CJK SC", "SimSun"),',
        f"  size: {fs:.1f}pt,",
        '  lang: "zh",',
        '  region: "CN",',
        ")",
        par_line,
        "",
        f"#let cw          = {fs:.2f}pt",
        f"#let heading_fw  = {heading_fw:.2f}pt",
        f"#let title_fw    = {title_fw:.2f}pt",
        f"#let subtitle_fw = {subtitle_fw:.2f}pt",
        f"#let author_fw   = {author_fw:.2f}pt",
        f"#let interp_fw   = {interp_fw:.2f}pt",
        f"#let note_fw     = {note_fw:.2f}pt",
        f"#let ns          = {note_fw:.2f}pt",
        f"#let pagenum_fw  = {pagenum_fw:.2f}pt",
        f"#let cs_r        = {cs_r_val:.4f}",
        "",
        *extras,
    ]
    return "\n".join(rows)


def _same_x_span(a: tuple, b: tuple, tol: float = 3.0) -> bool:
    return abs(a[0] - b[0]) <= tol and abs(a[2] - b[2]) <= tol


def _union_word_items(chars: list[CharData]) -> list[dict]:
    """把 OCR 词还原成横排词条。

    百度/腾讯按词返回后，竖排逻辑会把同一词切成「同 x1/x2、y 递增」的竖条。
    若词框偏宽，视为横排：合并为同一高度，从左到右还原文字。
    """
    if not chars:
        return []
    items: list[dict] = []
    i, n = 0, len(chars)
    while i < n:
        x1, y1, x2, y2 = chars[i].bbox
        j = i + 1
        while j < n and _same_x_span(chars[i].bbox, chars[j].bbox):
            j += 1
        group = chars[i:j]
        gx1 = min(c.bbox[0] for c in group)
        gy1 = min(c.bbox[1] for c in group)
        gx2 = max(c.bbox[2] for c in group)
        gy2 = max(c.bbox[3] for c in group)
        gw, gh = max(gx2 - gx1, 1.0), max(gy2 - gy1, 1.0)
        if len(group) > 1 and gw >= gh * 0.8:
            nch = len(group)
            cw = gw / nch
            restored: list[CharData] = []
            for k, c in enumerate(group):
                restored.append(CharData(
                    text=c.text,
                    bbox=(gx1 + k * cw, gy1, gx1 + (k + 1) * cw, gy2),
                    confidence=c.confidence,
                ))
            items.append({
                "text": "".join(c.text for c in group),
                "x1": gx1, "y1": gy1, "x2": gx2, "y2": gy2,
                "chars": restored,
            })
        else:
            for c in group:
                bx1, by1, bx2, by2 = c.bbox
                items.append({
                    "text": c.text,
                    "x1": bx1, "y1": by1, "x2": bx2, "y2": by2,
                    "chars": [c],
                })
        i = j
    return items


def _cluster_rows(
    items: list[dict],
    gap_px: float | None = None,
) -> list[list[dict]]:
    """JSON 高度相近的词在同一行（上→下）；行内按 x 左→右。"""
    if not items:
        return []
    heights = [max(1.0, it["y2"] - it["y1"]) for it in items]
    med_h = sorted(heights)[len(heights) // 2]
    gap = float(gap_px) if gap_px is not None else max(8.0, med_h * 0.55)
    tagged = [(float(it["y1"]), it) for it in items]
    tagged.sort(key=lambda t: t[0])
    rows: list[list[dict]] = []
    cur = [tagged[0][1]]
    cur_sum = tagged[0][0]
    cur_cnt = 1
    for y1, it in tagged[1:]:
        if abs(y1 - cur_sum / cur_cnt) <= gap:
            cur.append(it)
            cur_sum += y1
            cur_cnt += 1
        else:
            rows.append(cur)
            cur = [it]
            cur_sum = y1
            cur_cnt = 1
    rows.append(cur)
    for row in rows:
        row.sort(key=lambda it: (it["x1"], it["y1"]))
    return rows


def _merge_row_runs(row: list[dict], gap_factor: float = 1.5) -> list[dict]:
    """同一行内 x 间隙小的词并成一段，大间隙（如左标题右页码）分开 #place。"""
    if not row:
        return []
    widths = [max(1.0, it["x2"] - it["x1"]) for it in row]
    med_w = sorted(widths)[len(widths) // 2]
    runs: list[dict] = []
    cur = {
        "text": row[0]["text"],
        "x1": row[0]["x1"], "y1": row[0]["y1"],
        "x2": row[0]["x2"], "y2": row[0]["y2"],
        "chars": list(row[0]["chars"]),
    }
    for it in row[1:]:
        gap = it["x1"] - cur["x2"]
        if gap <= med_w * gap_factor:
            cur["text"] += it["text"]
            cur["x2"] = max(cur["x2"], it["x2"])
            cur["y1"] = min(cur["y1"], it["y1"])
            cur["y2"] = max(cur["y2"], it["y2"])
            cur["chars"].extend(it["chars"])
        else:
            runs.append(cur)
            cur = {
                "text": it["text"],
                "x1": it["x1"], "y1": it["y1"],
                "x2": it["x2"], "y2": it["y2"],
                "chars": list(it["chars"]),
            }
    runs.append(cur)
    return runs


def _classify_blocks(recs: list[dict], g: dict) -> list[tuple[str, str]]:
    title_max = int(g.get("title_max_chars", 12))
    note_max = int(g.get("note_max_chars", 6))
    recs_sorted = sorted(recs, key=lambda c: -c["col_cx_px"])
    blocks: list[tuple[str, str]] = []
    buf: list[str] = []

    def flush_main() -> None:
        if buf:
            blocks.append(("main", "".join(buf)))
            buf.clear()

    for col in recs_sorted:
        text = "".join(c.text for c in col["chars"]).strip()
        if not text:
            continue
        n = len(text)
        if n <= note_max:
            flush_main()
            blocks.append(("note", text))
        elif n <= title_max:
            flush_main()
            blocks.append(("title", text))
        else:
            buf.append(text)
    flush_main()
    return blocks


def _build_page(page: PageData, assets_dir: str, page_index: int,
                config: dict) -> str:
    g = config.get("guji_layout", {})
    show_num = bool(g.get("show_page_num", True))
    num_style = g.get("page_num_style", "arabic")
    page_offset = max(1, int(g.get("page_num_offset", 1)))
    htitle = g.get("header_title", "")
    hvol = g.get("header_volume", "")
    dpi = page.dpi

    tian_tou = _mm_to_pt(float(g.get("tian_tou_mm", 22)))
    di_jiao = _mm_to_pt(float(g.get("di_jiao_mm", 20)))
    zhuang_ding = _mm_to_pt(float(g.get("zhuang_ding_mm", 22)))
    shu_kou = _mm_to_pt(float(g.get("shu_kou_mm", 16)))
    pw, ph = _paper_dims_pt(g)
    bw = pw - zhuang_ding - shu_kou
    bh = ph - tian_tou - di_jiao

    all_chars: list[CharData] = []
    for col in page.text_columns:
        all_chars.extend(col.chars)
    recs = _recluster_chars(all_chars, dpi, gap_px=35)
    blocks = _classify_blocks(recs, g)

    lns: list[str] = []
    if page_index > 0:
        lns += ["#pagebreak()", ""]

    lns += [
        f'// {"=" * 60}',
        f'// 第 {page.page_num} 页  简体横排  块={len(blocks)}'
        f'  版心={bw:.0f}x{bh:.0f}pt  装订=左翻',
        f'// {"=" * 60}',
        "",
    ]
    if htitle or hvol:
        lns.append(f'#align(center)[{_esc((htitle + " " + hvol).strip())}]')
        lns.append("")

    display_num = page.page_num - (page_offset - 1)
    show_num_here = show_num and display_num > 0
    num = (_to_chinese_numeral(display_num)
           if num_style == "chinese" else str(display_num))

    lns.append(f"#block(width: {bw:.1f}pt, height: {max(bh - 1.0, 1):.1f}pt)[")
    if show_num_here:
        lns.append(f"  #place(bottom + center)[#text(size: pagenum_fw)[{num}]]")
    if not blocks:
        lns.append("  // （空页）")
    else:
        lns.append("  #set text(dir: ltr)")
        for kind, text in blocks:
            esc = _esc(text)
            if kind == "title":
                lns.append(f"  #htitle[{esc}]")
            elif kind == "note":
                lns.append(f"  #par(first-line-indent: 0em)[#hnote[{esc}]]")
            else:
                lns.append(f"  #par[{esc}]")
    lns.append("]")

    for ii, ir in enumerate(page.image_regions):
        fn = f"p{page.page_num}_img_{ii + 1:03d}.png"
        fabs = os.path.join(assets_dir, fn)
        os.makedirs(assets_dir, exist_ok=True)
        open(fabs, "wb").write(ir.image_bytes)
        iw = _px_to_pt(ir.bbox[2] - ir.bbox[0], dpi)
        ih = _px_to_pt(ir.bbox[3] - ir.bbox[1], dpi)
        rel = os.path.join("assets", fn).replace("\\", "/")
        lns += [f'#image("{rel}", width: {iw:.1f}pt, height: {ih:.1f}pt)', ""]

    return "\n".join(lns)


def _build_abs_page(page: PageData, assets_dir: str, page_index: int,
                    config: dict) -> str:
    """按 OCR JSON 像素坐标等比换算到版心，#place 各词。"""
    g = config.get("guji_layout", {})
    fs = float(config.get("font_size", 12))
    show_num = bool(g.get("show_page_num", True))
    num_style = g.get("page_num_style", "arabic")
    page_offset = max(1, int(g.get("page_num_offset", 1)))
    htitle = g.get("header_title", "")
    hvol = g.get("header_volume", "")

    tian_tou = _mm_to_pt(float(g.get("tian_tou_mm", 22)))
    di_jiao = _mm_to_pt(float(g.get("di_jiao_mm", 20)))
    zhuang_ding = _mm_to_pt(float(g.get("zhuang_ding_mm", 22)))
    shu_kou = _mm_to_pt(float(g.get("shu_kou_mm", 16)))
    pw, ph = _paper_dims_pt(g)
    bw = pw - zhuang_ding - shu_kou
    bh = ph - tian_tou - di_jiao

    orig_w = max(float(page.orig_width_px), 1.0)
    orig_h = max(float(page.orig_height_px), 1.0)
    sx = bw / orig_w
    sy = bh / orig_h

    all_chars: list[CharData] = []
    for col in page.text_columns:
        all_chars.extend(col.chars)
    items = _union_word_items(all_chars)
    rows = _cluster_rows(items)

    lns: list[str] = []
    if page_index > 0:
        lns += ["#pagebreak()", ""]

    lns += [
        f'// {"=" * 60}',
        f'// 第 {page.page_num} 页  横排绝对坐标  行={len(rows)} 词={len(items)}'
        f'  原图像素={orig_w:.0f}x{orig_h:.0f}'
        f'  版心={bw:.0f}x{bh:.0f}pt  sx={sx:.4f} sy={sy:.4f}',
        f'// {"=" * 60}',
        "",
    ]
    if htitle or hvol:
        lns.append(f'#align(center)[{_esc((htitle + " " + hvol).strip())}]')
        lns.append("")

    display_num = page.page_num - (page_offset - 1)
    show_num_here = show_num and display_num > 0
    num = (_to_chinese_numeral(display_num)
           if num_style == "chinese" else str(display_num))

    lns.append("// 版心 block：dx=x/页宽×版心宽  dy=y/页高×版心高")
    lns.append(f"#block(width: {bw:.1f}pt, height: {max(bh - 1.0, 1):.1f}pt)[")
    if show_num_here:
        lns.append(f"  #place(bottom + center)[#text(size: pagenum_fw)[{num}]]")
    if not rows:
        lns.append("  // （空页）")
    else:
        lns.append("  #set text(dir: ltr)")
        for ri, row in enumerate(rows):
            y_px = min(it["y1"] for it in row)
            dy = max(0.0, min(y_px * sy, max(bh - fs, 0.0)))
            row_text = "".join(it["text"] for it in row)
            lns.append(
                f"  // 行{ri + 1:2d}: y={y_px:.0f}px  dy={dy:.1f}pt  {row_text}"
            )
            for it in _merge_row_runs(row):
                text = it["text"]
                if not text.strip():
                    continue
                dx = max(0.0, min(it["x1"] * sx, max(bw - fs, 0.0)))
                esc = _esc(text)
                lns.append(
                    f"  #place(top + left, dx: {dx:.1f}pt, dy: {dy:.1f}pt)"
                    f'[#hrow("{esc}")]'
                )

    for ii, ir in enumerate(page.image_regions):
        fn = f"p{page.page_num}_img_{ii + 1:03d}.png"
        fabs = os.path.join(assets_dir, fn)
        os.makedirs(assets_dir, exist_ok=True)
        open(fabs, "wb").write(ir.image_bytes)
        ix = ir.bbox[0] * sx
        iy = ir.bbox[1] * sy
        iw = (ir.bbox[2] - ir.bbox[0]) * sx
        ih = (ir.bbox[3] - ir.bbox[1]) * sy
        rel = os.path.join("assets", fn).replace("\\", "/")
        lns.append(
            f"  #place(top + left, dx: {ix:.1f}pt, dy: {iy:.1f}pt)"
            f'[#image("{rel}", width: {iw:.1f}pt, height: {ih:.1f}pt)]'
        )

    lns.append("]")
    return "\n".join(lns)


def create_typst(pages: list[PageData], output_path: str, config: dict,
                 flow: bool = False) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    assets_dir = os.path.join(os.path.dirname(output_path) or ".", "assets")
    parts: list[str] = [_build_header(config, flow=flow)]
    builder = _build_page if flow else _build_abs_page
    for idx, page in enumerate(pages):
        parts.append(builder(page, assets_dir, idx, config))
    with open(output_path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(parts))
