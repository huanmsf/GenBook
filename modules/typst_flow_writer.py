"""typst_flow_writer.py — 流式 grid 竖排排版。

与 typst_writer.py（绝对坐标模式）的区别
-----------------------------------------
- 每页用 #grid(columns: ...) 承载所有列，**列顺序即显示顺序**
- #set text(dir: rtl)：grid 从右向左展开，第1子项 = 最右列（书口）
- 版心不足时在 grid 末尾自动补空列 []，使内容列始终贴右边
- 插/删列只需增删 grid 子项，右侧（书口侧）列不受影响
- 仍可通过 create_typst(..., flow=False) 回退到绝对坐标模式

公开 API
---------
    create_typst(pages, output_path, config, flow=True)
        与 typst_writer.create_typst 签名完全相同，可直接替换调用。
"""
from __future__ import annotations

import os
from modules.page_model import PageData, CharData


# ---------------------------------------------------------------------------
# 常量 & 工具函数（与 typst_writer 共用逻辑，避免循环 import）
# ---------------------------------------------------------------------------

_PAPER_PT: dict[str, tuple[float, float]] = {
    "jis-b5":  (515.91, 728.50),
    "jis-b4":  (728.50, 1031.81),
    "a4":      (595.28, 841.89),
    "a5":      (419.53, 595.28),
    "letter":  (612.00, 792.00),
    "b5":      (498.90, 708.66),
}

_ESC: dict[str, str] = {
    '\\': '\\\\', '#': '\\#', '@': '\\@', '<': '\\<', '>': '\\>',
    '*': '\\*',   '`': '\\`', '$': '\\$', '=': '\\=', '~': '\\~',
    "'": "\\'",   '"': '\\"', '[': '\\[', ']': '\\]',
}


def _esc(text: str) -> str:
    return ''.join(_ESC.get(ch, ch) for ch in text)


def _px_to_pt(px: float, dpi: int) -> float:
    return px * 72.0 / dpi


def _mm_to_pt(mm: float) -> float:
    return mm * 72.0 / 25.4


def _paper_content_size(paper: str, tian_tou: float, di_jiao: float,
                        zhuang_ding: float, shu_kou: float) -> tuple[float, float]:
    pw, ph = _PAPER_PT.get(paper.lower(), (515.91, 728.50))
    return pw - zhuang_ding - shu_kou, ph - tian_tou - di_jiao


def _to_chinese_numeral(num: int) -> str:
    digits = '零一二三四五六七八九'
    units  = ['', '十', '百', '千', '万']
    if num <= 0:  return digits[0]
    if num < 10:  return digits[num]
    result = ''
    mag = 1
    while 10 ** mag <= num:
        mag += 1
    for i in range(mag - 1, -1, -1):
        d = (num // (10 ** i)) % 10
        if d == 0:
            if result and result[-1] != '零':
                result += '零'
        else:
            result += digits[d] + units[i]
    result = result.rstrip('零')
    if result.startswith('一十'):
        result = result[1:]
    return result


# ---------------------------------------------------------------------------
# 列重聚类（与 typst_writer 相同算法）
# ---------------------------------------------------------------------------

def _recluster_chars(chars: list[CharData], dpi: int,
                     gap_px: int = 35) -> list[dict]:
    """按字符 cx 坐标聚类，重建列结构（从右到左，source_order=1=最右）。"""
    if not chars:
        return []
    tagged = sorted([(((c.bbox[0]+c.bbox[2])/2.0), c) for c in chars],
                    key=lambda t: -t[0])
    clusters: list[list] = []
    cur_grp  = [tagged[0]]
    cur_sum  = tagged[0][0]
    cur_cnt  = 1
    for cx, c in tagged[1:]:
        if abs(cx - cur_sum / cur_cnt) <= gap_px:
            cur_grp.append((cx, c)); cur_sum += cx; cur_cnt += 1
        else:
            clusters.append(cur_grp)
            cur_grp = [(cx, c)]; cur_sum = cx; cur_cnt = 1
    clusters.append(cur_grp)
    result = []
    for i, grp in enumerate(clusters):
        col_cx = sum(x for x, _ in grp) / len(grp)
        col_chars = sorted([c for _, c in grp], key=lambda c: c.bbox[1])
        result.append({'source_order': i + 1,
                       'col_cx_px': col_cx,
                       'chars': col_chars})
    return result


# ---------------------------------------------------------------------------
# 头部生成（与 typst_writer._build_header 保持一致，额外加流式 banner）
# ---------------------------------------------------------------------------

_FLOW_BANNER = """\
// ╔══════════════════════════════════════════════════════════════════╗
// ║  GenBook 流式竖排版  (typst_flow_writer.py 自动生成)             ║
// ║                                                                  ║
// ║  编辑指南：                                                      ║
// ║  · 每页是一个 #grid(...)，列顺序 = 显示顺序（右→左）            ║
// ║  · 插入空列：在 grid 中加一个 []                                 ║
// ║  · 删除/移动列：直接剪切 grid 子项到目标位置                     ║
// ║  · 列首字下沉（dy）：修改 pad(top: Xpt) 中的值                  ║
// ║  · 换页：把 grid 子项剪切到下一页的 grid 开头                    ║
// ║  · 子项顺序=视觉右→左（第1项=最右列）；插列后右侧列不动，左侧左移 ║
// ╚══════════════════════════════════════════════════════════════════╝"""


def _build_header(config: dict, flow: bool = True) -> str:
    ff      = config.get('font_family', 'STKaiTi')
    fs      = float(config.get('font_size', 12))
    ns      = float(config.get('note_font_size', 8))
    _ls_raw = float(config.get('line_spacing', 0))
    ls      = _ls_raw if _ls_raw > 0 else round(fs * 0.20, 2)
    g       = config.get('guji_layout', {})
    paper        = g.get('paper', 'jis-b5')
    tmpl         = g.get('template', 'blank')
    tian_tou     = _mm_to_pt(float(g.get('tian_tou_mm',    25)))
    di_jiao      = _mm_to_pt(float(g.get('di_jiao_mm',     20)))
    zhuang_ding  = _mm_to_pt(float(g.get('zhuang_ding_mm', 20)))
    shu_kou      = _mm_to_pt(float(g.get('shu_kou_mm',     15)))
    st           = g.get('styles', {})

    def _fw(key: str, default: float) -> float:
        return round(fs * float(st.get(key, default)), 2)

    heading_fw  = _fw('heading_scale',  1.50)
    title_fw    = _fw('title_scale',    1.30)
    subtitle_fw = _fw('subtitle_scale', 1.00)
    author_fw   = _fw('author_scale',   0.80)
    interp_fw   = _fw('interp_scale',   0.80)
    note_fw     = _fw('note_scale',     0.54)
    pagenum_fw  = _fw('pagenum_scale',  0.70)
    cs_r_val    = round(ls / fs, 4)
    mode_tag    = '流式grid竖排' if flow else '绝对坐标竖排'

    rows = [
        _FLOW_BANNER if flow else f'// GenBook — {mode_tag}',
        '',
        f'// 模板：{tmpl}  正文:{fs}pt  纸张:{paper}  模式:{mode_tag}',
        '',
        '// ── #set 规则放最前（避免中间空行产生额外空页）──────────',
        '#set page(',
        f'  paper: "{paper}",',
        f'  margin: (top: {tian_tou:.1f}pt, bottom: {di_jiao:.1f}pt,',
        f'           left: {shu_kou:.1f}pt, right: {zhuang_ding:.1f}pt)',
        ')',
        '#set text(',
        f'  font: ("{ff}", "Noto Serif CJK TC", "SimSun"),',
        f'  size: {fs:.1f}pt,',
        '  lang: "zh"',
        ')',
        '#set par(leading: 0pt, spacing: 0pt)',
        '',
        '// ── 字号变量（修改 config/layout_config.yaml → styles 节即可）──',
        f'#let cw          = {fs:.2f}pt',
        f'#let heading_fw  = {heading_fw:.2f}pt',
        f'#let title_fw    = {title_fw:.2f}pt',
        f'#let subtitle_fw = {subtitle_fw:.2f}pt',
        f'#let author_fw   = {author_fw:.2f}pt',
        f'#let interp_fw   = {interp_fw:.2f}pt',
        f'#let note_fw     = {note_fw:.2f}pt',
        f'#let ns          = {note_fw:.2f}pt',
        f'#let pagenum_fw  = {pagenum_fw:.2f}pt',
        f'#let cs_r        = {cs_r_val:.4f}',
        '',
        '// ── 核心竖排函数 vcol ────────────────────────────────────',
        '#let vcol(s, fw: cw) = {',
        '  stack(dir: ttb,',
        '    ..s.clusters().map(c =>',
        '      box(width: fw, height: fw * (1 + cs_r))[#align(center + horizon)[#text(size: fw)[#c]]]',
        '    )',
        '  )',
        '}',
        '',
        '// ── 快捷样式函数 ────────────────────────────────────────',
        '#let vmain(s)     = vcol(s, fw: cw)',
        '#let vheading(s)  = vcol(s, fw: heading_fw)',
        '#let vtitle(s)    = vcol(s, fw: title_fw)',
        '#let vsubtitle(s) = vcol(s, fw: subtitle_fw)',
        '#let vauthor(s)   = vcol(s, fw: author_fw)',
        '#let vinterp(s)   = vcol(s, fw: interp_fw)',
        '#let vnote(s)     = vcol(s, fw: note_fw)',
        '',
    ]
    return '\n'.join(rows)


# ---------------------------------------------------------------------------
# dy snap 辅助
# ---------------------------------------------------------------------------

def _compute_snapped_dy(recs: list[dict], dpi: int,
                        fs: float, ls: float,
                        snap_chars: float) -> list[float]:
    """计算每列首字相对版心顶的 dy（pt），并做 snap 对齐。"""
    snap_thresh = (fs + ls) * snap_chars
    all_y1 = [_px_to_pt(col['chars'][0].bbox[1], dpi)
              for col in recs if col['chars']]
    ocr_y_min = min(all_y1) if all_y1 else 0.0
    raw_dy: list[float] = []
    for col in recs:
        if col['chars']:
            y1_pt = _px_to_pt(col['chars'][0].bbox[1], dpi)
            raw_dy.append(y1_pt - ocr_y_min)
        else:
            raw_dy.append(0.0)

    if not raw_dy:
        return raw_dy

    indexed = sorted(enumerate(raw_dy), key=lambda t: t[1])
    groups: list[list[int]] = [[indexed[0][0]]]
    for idx, dy in indexed[1:]:
        if dy - raw_dy[groups[-1][0]] <= snap_thresh:
            groups[-1].append(idx)
        else:
            groups.append([idx])
    snapped = list(raw_dy)
    for grp in groups:
        min_dy = min(raw_dy[i] for i in grp)
        for i in grp:
            snapped[i] = min_dy
    return snapped


# ---------------------------------------------------------------------------
# 流式页块生成
# ---------------------------------------------------------------------------

def _build_flow_page(page: PageData, assets_dir: str, page_index: int,
                     config: dict) -> str:
    """生成一页的流式 grid 竖排 Typst 代码。"""
    g            = config.get('guji_layout', {})
    fs           = float(config.get('font_size', 12))
    _ls_raw      = float(config.get('line_spacing', 0))
    ls           = _ls_raw if _ls_raw > 0 else round(fs * 0.20, 2)
    col_spacing  = float(config.get('column_spacing', 4))
    tmpl         = g.get('template', 'blank')
    show_num     = bool(g.get('show_page_num', True))
    num_style    = g.get('page_num_style', 'chinese')
    htitle       = g.get('header_title', '')
    hvol         = g.get('header_volume', '')
    dpi          = page.dpi
    snap_chars   = float(g.get('snap_chars', 2))

    tian_tou    = _mm_to_pt(float(g.get('tian_tou_mm',    25)))
    di_jiao     = _mm_to_pt(float(g.get('di_jiao_mm',     20)))
    zhuang_ding = _mm_to_pt(float(g.get('zhuang_ding_mm', 20)))
    shu_kou     = _mm_to_pt(float(g.get('shu_kou_mm',     15)))
    paper       = g.get('paper', 'jis-b5')
    bw, bh      = _paper_content_size(paper, tian_tou, di_jiao,
                                      zhuang_ding, shu_kou)

    all_chars: list[CharData] = []
    for col in page.text_columns:
        all_chars.extend(col.chars)
    recs = _recluster_chars(all_chars, dpi, gap_px=35)

    lns: list[str] = []
    if page_index > 0:
        lns += ['#pagebreak()', '']

    side = '右→左' if page.page_num % 2 == 1 else '左→右'
    lns += [
        f'// {"="*60}',
        f'// 第 {page.page_num} 页  {tmpl}  重分列={len(recs)}列'
        f'  版心={bw:.0f}x{bh:.0f}pt  装订={side}',
        f'// {"="*60}',
        '',
    ]

    if htitle or hvol:
        lns.append(
            f'#align(center)[{_esc((htitle + " " + hvol).strip())}]')
        lns.append('')

    num = (_to_chinese_numeral(page.page_num)
           if num_style == 'chinese' else str(page.page_num))

    # ── 空白页 ────────────────────────────────────────────────────────
    if not recs:
        lns += [
            f'// （空页）',
            f'#block(width: {bw:.1f}pt, height: {bh:.1f}pt)[',
        ]
        if show_num:
            lns.append(
                f'  #place(bottom + center)[#text(size: pagenum_fw)[{num}]]')
        lns.append(']')
        return '\n'.join(lns)

    # ── 计算 snapped dy ──────────────────────────────────────────────
    snapped_dy = _compute_snapped_dy(recs, dpi, fs, ls, snap_chars)

    # ── 列按 col_cx 降序（右→左），配合 dir:rtl 使第1子项=最右列 ─────
    recs_sorted = sorted(recs, key=lambda c: -c['col_cx_px'])

    # ── 版心容量与补列 ────────────────────────────────────────────────
    n         = len(recs_sorted)
    max_cols  = max(1, int(bw / (fs + col_spacing)))
    overflow  = max(0, n - max_cols)
    pad_cols  = max(0, max_cols - n)
    cap_note  = (f'容量{max_cols}列/当前{n}列  '
                 + (f'⚠ 溢出{overflow}列→左边可见'
                    if overflow else f'✓ 未溢出 补{pad_cols}空列'))

    # columns 宽度字符串：内容列 + 末尾补列（dir:rtl 下末尾=视觉最左）
    col_widths = ', '.join(['(cw)'] * n + ['(cw)'] * pad_cols)

    lns += [
        f'// 版心 {bw:.1f}×{bh:.1f}pt  {cap_note}',
        f'// ★ 子项顺序=视觉右→左（第1项=最右/书口列）',
        f'// ★ 插列：在位置K前加子项 → K及左侧自动左移，右侧不动',
        f'// ★ 删列：删子项 → 右侧列自动右移（向书口靠拢）',
        f'// ★ 空列：插入 []  移列：剪切子项到目标位置',
        f'#block(width: {bw:.1f}pt, height: {bh:.1f}pt)[  // 版心宽高',
    ]
    if show_num:
        lns.append(
            f'  #place(bottom + center)[#text(size: pagenum_fw)[{num}]]')
    lns += [
        f'  // dir:rtl：grid 从右向左展开；末尾补{pad_cols}个空列使内容列贴右',
        f'  #set text(dir: rtl)',
        f'  #grid(',
        f'    columns: ({col_widths}),',
        f'    column-gutter: {col_spacing:.1f}pt,',
        f'    align: top,',
    ]

    # ── 各内容列子项 ──────────────────────────────────────────────────
    for ci, col in enumerate(recs_sorted):
        chars  = col['chars']
        order  = col['source_order']
        n_char = len(chars)
        # 从 snapped_dy 中找对应项（recs_sorted 是 recs 的重排序，需映射回原始索引）
        orig_idx = recs.index(col)
        dy_pt  = snapped_dy[orig_idx] if snapped_dy else 0.0
        dy_pt  = max(0.0, min(dy_pt, bh - fs))
        text   = _esc(''.join(c.text for c in chars))
        comma  = ',' if (ci < n - 1 or pad_cols > 0) else ''
        lns.append(f'    // 列{order}(main) {n_char}字  dy={dy_pt:.1f}pt')
        if dy_pt > 0.5:
            lns.append(
                f'    box(height: {bh:.1f}pt)[#pad(top: {dy_pt:.1f}pt)'
                f'[#vcol("{text}", fw: cw)]]{comma}')
        else:
            lns.append(
                f'    box(height: {bh:.1f}pt)[#vcol("{text}", fw: cw)]{comma}')

    # ── 补列（末尾空列，视觉最左，使内容列贴右） ──────────────────────
    for pi in range(pad_cols):
        comma = ',' if pi < pad_cols - 1 else ''
        lns.append(f'    []{comma}')

    lns += [
        f'  )  // end grid p{page.page_num}',
        ']',
    ]

    # ── 图片区域（附加在页块外） ──────────────────────────────────────
    for ii, ir in enumerate(page.image_regions):
        fn   = f'p{page.page_num}_img_{ii+1:03d}.png'
        fabs = os.path.join(assets_dir, fn)
        os.makedirs(assets_dir, exist_ok=True)
        open(fabs, 'wb').write(ir.image_bytes)
        iw  = _px_to_pt(ir.bbox[2] - ir.bbox[0], dpi)
        ih  = _px_to_pt(ir.bbox[3] - ir.bbox[1], dpi)
        rel = os.path.join('assets', fn).replace('\\', '/')
        lns += [f'#image("{rel}", width: {iw:.1f}pt, height: {ih:.1f}pt)', '']

    return '\n'.join(lns)


# ---------------------------------------------------------------------------
# 公开入口
# ---------------------------------------------------------------------------

def create_typst(pages: list[PageData], output_path: str,
                 config: dict, flow: bool = True) -> None:
    """生成 Typst 竖排源文件。

    Parameters
    ----------
    pages       : OCR 处理后的页列表。
    output_path : 输出 .typ 文件路径。
    config      : layout_config.yaml 加载后的字典。
    flow        : True（默认）→ 流式 grid 模式；
                  False → 绝对坐标模式（委托给 typst_writer）。
    """
    if not flow:
        # 回退到绝对坐标模式
        from modules.typst_writer import create_typst as _abs_create
        _abs_create(pages, output_path, config)
        return

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    assets_dir = os.path.join(os.path.dirname(output_path) or '.', 'assets')

    parts: list[str] = [_build_header(config, flow=True)]
    for idx, page in enumerate(pages):
        parts.append(_build_flow_page(page, assets_dir, idx, config))

    content = '\n'.join(parts)
    with open(output_path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(content)
