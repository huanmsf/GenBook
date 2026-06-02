"""typst_writer.py v9 — 字符坐标重分列 + #place 绝对定位竖排。"""
from __future__ import annotations
import os
from modules.page_model import PageData, CharData


def build_typ_output_path(pdf_path: str) -> str:
    root, _ = os.path.splitext(pdf_path)
    return root + '.typ'


_ESC: dict[str, str] = {
    '\\': '\\\\',
    '#': '\\#',
    '@': '\\@',
    '<': '\\<',
    '>': '\\>',
    '*': '\\*',
    '`': '\\`',
    '$': '\\$',
    '=': '\\=',
    '~': '\\~',
    "'": "\\'",
    '"': '\\"',
    '[': '\\[',
    ']': '\\]',
}


def _escape_typst(text: str) -> str:
    return ''.join(_ESC.get(ch, ch) for ch in text)


def _px_to_pt(px: float, dpi: int) -> float:
    return px * 72.0 / dpi


def _mm_to_pt(mm: float) -> float:
    return mm * 72.0 / 25.4


def _to_chinese_numeral(num: int) -> str:
    digits = '零一二三四五六七八九'
    if num <= 0:  return digits[0]
    if num < 10:  return digits[num]
    if num == 10: return '十'
    if num < 20:  return '十' + digits[num % 10]
    tens, ones = divmod(num, 10)
    return digits[tens] + '十' + (digits[ones] if ones else '')


def _recluster_chars(
    chars: list[CharData],
    dpi: int,
    gap_px: int = 35,
) -> list[dict]:
    """按字符 cx 坐标聚类，重建列结构（从右到左，source_order=1=最右）。"""
    if not chars:
        return []
    tagged = []
    for c in chars:
        bx1, by1, bx2, by2 = c.bbox
        cx = (bx1 + bx2) / 2.0
        tagged.append((cx, c))
    tagged.sort(key=lambda t: -t[0])  # 右→左
    clusters: list[list] = []
    cur_sum = tagged[0][0]; cur_cnt = 1; cur_grp = [tagged[0]]
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


def _classify(n: int, col_cx_px: float, page_w_px: int) -> str:
    if n == 0: return 'empty'
    if col_cx_px >= page_w_px * 0.85 and n <= 8: return 'title'
    if n <= 4: return 'note'
    return 'main'


def _build_header(config: dict) -> str:
    ff  = config.get('font_family', 'STKaiTi')
    fs  = float(config.get('font_size', 12))
    ns  = float(config.get('note_font_size', 8))
    _ls_raw = float(config.get('line_spacing', 0))
    ls  = _ls_raw if _ls_raw > 0 else round(fs * 0.20, 2)  # 默认=字号20%（标准行距）
    g   = config.get('guji_layout', {})
    paper       = g.get('paper', 'jis-b5')
    tmpl        = g.get('template', 'blank')
    tian_tou    = _mm_to_pt(float(g.get('tian_tou_mm',    25)))
    di_jiao     = _mm_to_pt(float(g.get('di_jiao_mm',     20)))
    zhuang_ding = _mm_to_pt(float(g.get('zhuang_ding_mm', 20)))
    shu_kou     = _mm_to_pt(float(g.get('shu_kou_mm',     15)))
    rows = [
        '// GenBook v9 — 字符坐标重分列 + place 绝对定位竖排',
        f'// 模板：{tmpl}',
        '',
        '#set text(',
        f'  font: ("{ff}", "Noto Serif CJK TC", "SimSun"),',
        f'  size: {fs:.1f}pt,',
        '  lang: "zh"',
        ')',
        '#set par(leading: 0pt, spacing: 0pt)',
        f'#let cw = {fs:.1f}pt',
        f'#let ns = {ns:.1f}pt',
        f'#let cs_r = {ls/fs:.4f}  // char_spacing ratio (={ls:.2f}pt / {fs:.1f}pt)',
        '#set page(',
        f'  paper: "{paper}",',
        f'  margin: (top: {tian_tou:.1f}pt, bottom: {di_jiao:.1f}pt,',
        f'           left: {shu_kou:.1f}pt, right: {zhuang_ding:.1f}pt)',
        ')',
        '',
        '// vcol: 逐字竖排 — stack(dir: ttb) 保证从上到下',
        '#let vcol(s, fw: cw) = {',
        '  stack(dir: ttb,',
        '    ..s.clusters().map(c =>',
        '      box(width: fw, height: fw * (1 + cs_r))[#align(center + horizon)[#text(size: fw)[#c]]]',
        '    )',
        '  )',
        '}',
        '',
    ]
    return '\n'.join(rows)


def _build_page_block(page: PageData, assets_dir: str,
                      page_index: int, config: dict) -> str:
    g    = config.get('guji_layout', {})
    fs   = float(config.get('font_size', 12))
    ns   = float(config.get('note_font_size', 8))
    _ls_raw     = float(config.get('line_spacing', 0))
    ls          = _ls_raw if _ls_raw > 0 else round(fs * 0.20, 2)  # 默认=字号20%
    col_spacing = float(config.get('column_spacing', 4))
    tmpl = g.get('template', 'blank')
    show_num  = bool(g.get('show_page_num', True))
    num_style = g.get('page_num_style', 'chinese')
    htitle    = g.get('header_title', '')
    hvol      = g.get('header_volume', '')
    dpi       = page.dpi

    tian_tou    = _mm_to_pt(float(g.get('tian_tou_mm',    25)))
    di_jiao     = _mm_to_pt(float(g.get('di_jiao_mm',     20)))
    zhuang_ding = _mm_to_pt(float(g.get('zhuang_ding_mm', 20)))
    shu_kou     = _mm_to_pt(float(g.get('shu_kou_mm',     15)))
    page_w_pt   = _px_to_pt(page.orig_width_px,  dpi)
    page_h_pt   = _px_to_pt(page.orig_height_px, dpi)
    banxin_w    = page_w_pt  - zhuang_ding - shu_kou
    banxin_h    = page_h_pt  - tian_tou    - di_jiao

    all_chars: list[CharData] = []
    for col in page.text_columns:
        all_chars.extend(col.chars)
    recs = _recluster_chars(all_chars, dpi, gap_px=35)

    # ── dy snap：计算每列首字 dy，相差 ≤N字高的列对齐到组内最小值 ──
    snap_chars  = float(g.get('snap_chars', 2))
    snap_thresh = (fs + ls) * snap_chars
    all_y1 = [_px_to_pt(col['chars'][0].bbox[1], dpi) for col in recs if col['chars']]
    ocr_y_min = min(all_y1) if all_y1 else 0.0
    all_y1 = [_px_to_pt(col['chars'][0].bbox[1], dpi) for col in recs if col['chars']]
    ocr_y_min = min(all_y1) if all_y1 else 0.0
    raw_dy: list[float] = []
    for col in recs:
        if col['chars']:
            y1_pt = _px_to_pt(col['chars'][0].bbox[1], dpi)
            raw_dy.append(y1_pt - ocr_y_min)
        else:
            raw_dy.append(0.0)

    # 分组：将所有 dy 排序，相差 ≤ snap_thresh 的归一组，组内取最小值
    if raw_dy:
        indexed = sorted(enumerate(raw_dy), key=lambda t: t[1])
        groups: list[list[int]] = [[indexed[0][0]]]
        for (idx, dy) in indexed[1:]:
            if dy - raw_dy[groups[-1][0]] <= snap_thresh:
                groups[-1].append(idx)
            else:
                groups.append([idx])
        snapped_dy: list[float] = list(raw_dy)
        for grp in groups:
            min_dy = min(raw_dy[i] for i in grp)
            for i in grp:
                snapped_dy[i] = min_dy

    lns: list[str] = []
    if page_index > 0:
        lns += ['#pagebreak()', '']

    side = '右→左' if page.page_num % 2 == 1 else '左→右'
    lns.append(
        f'// === 第 {page.page_num} 页  {tmpl}'
        f'  重分列={len(recs)}列'
        f'  原PDF={page_w_pt:.0f}x{page_h_pt:.0f}pt'
        f'  版心={banxin_w:.0f}x{banxin_h:.0f}pt  装订={side} ==='
    )
    lns.append('')

    if htitle or hvol:
        lns.append(f'#align(center)[{_escape_typst((htitle + " " + hvol).strip())}]')
        lns.append('')

    # 修复1：页码用 #place(bottom+center) 固定在版心底部，不占文档流
    if show_num:
        num = _to_chinese_numeral(page.page_num) if num_style == 'chinese' else str(page.page_num)
        lns.append(f'// 版心 block（含页码绝对定位）')
        lns.append(f'#block(width: {banxin_w:.1f}pt, height: {banxin_h:.1f}pt)[')
        lns.append(f'  #place(bottom + center)[{num}]')
    else:
        lns.append(f'#block(width: {banxin_w:.1f}pt, height: {banxin_h:.1f}pt)[')

    for ci, col in enumerate(recs):
        n       = len(col['chars'])
        cx_px   = col['col_cx_px']
        order   = col['source_order']
        ctype   = _classify(n, cx_px, page.orig_width_px)
        fw_expr = 'ns' if ctype == 'note' else 'cw'
        fw_val  = ns    if ctype == 'note' else fs
        ls_ratio = ls / fs  # 相对行距比例
        h_pt    = n * fw_val * (1 + ls_ratio)

        # x_left: 从版心右边起，按 source_order 固定步长从右到左排列
        col_step = fs + col_spacing      # 统一用正文字号，保证 note 列不错位
        x_left   = banxin_w - fw_val - (order - 1) * col_step

        # dy: snap 后的版心顶偏移
        dy_pt = snapped_dy[ci] if raw_dy else 0.0

        text = _escape_typst(''.join(c.text for c in col['chars']))
        lns.append(
            f'  // 列{order:2d}: {ctype:5s}  字数={n:3d}'
            f'  cx={cx_px:.0f}px  x_left={x_left:.1f}pt  dy={dy_pt:.1f}pt'
        )
        if text.strip():
            col_body = (f'box(width: {fw_expr}, height: {h_pt:.1f}pt)'
                        f'[#vcol("{text}", fw: {fw_expr})]')
        else:
            col_body = f'box(width: {fw_expr}, height: {h_pt:.1f}pt)[]'
        lns.append(f'  #place(top + left, dx: {x_left:.1f}pt, dy: {dy_pt:.1f}pt, {col_body})')

    lns.append(']')

    for ii, ir in enumerate(page.image_regions):
        fn   = f'p{page.page_num}_img_{ii+1:03d}.png'
        fabs = os.path.join(assets_dir, fn)
        os.makedirs(assets_dir, exist_ok=True)
        open(fabs, 'wb').write(ir.image_bytes)
        iw = _px_to_pt(ir.bbox[2]-ir.bbox[0], dpi)
        ih = _px_to_pt(ir.bbox[3]-ir.bbox[1], dpi)
        rel = os.path.join('assets', fn).replace('\\', '/')
        lns.append(f'#image("{rel}", width: {iw:.1f}pt, height: {ih:.1f}pt)')
        lns.append('')

    return '\n'.join(lns)


def create_typst(pages: list[PageData], output_path: str, config: dict) -> None:
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    assets_dir = os.path.join(os.path.dirname(output_path) or '.', 'assets')
    parts2 = [_build_header(config)]
    for idx, page in enumerate(pages):
        parts2.append(_build_page_block(page, assets_dir, idx, config))
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(parts2))
