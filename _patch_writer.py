"""Patch typst_writer.py: x_left fix, dy fix, char_spacing support."""
import pathlib, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

p = pathlib.Path('modules/typst_writer.py')
s = p.read_text(encoding='utf-8')


def _p(s, old, new, tag):
    if old in s:
        print(f'  OK: {tag}')
        return s.replace(old, new, 1)
    print(f'  SKIP: {tag}')
    return s

# 1. _build_header: add ls (line_spacing) param
s = _p(s,
    "    ns  = float(config.get('note_font_size', 8))\n    g   = config.get('guji_layout', {})",
    "    ns  = float(config.get('note_font_size', 8))\n    ls  = float(config.get('line_spacing', 0))\n    g   = config.get('guji_layout', {})",
    'header add ls')

# 2. inject #let cs Typst variable
s = _p(s,
    "        f'#let ns = {ns:.1f}pt',\n        '#set page(',",
    "        f'#let ns = {ns:.1f}pt',\n        f'#let cs = {ls:.2f}pt  // char_spacing',\n        '#set page(',",
    'inject cs var')

# 3. vcol box height: fw -> fw + cs
s = _p(s,
    'box(width: fw, height: fw)[#align(center + horizon)[#c]]',
    'box(width: fw, height: fw + cs)[#align(center + horizon)[#c]]',
    'vcol box height')

# 4. _build_page_block: add ls
s = _p(s,
    "    ns   = float(config.get('note_font_size', 8))\n    tmpl = g.get('template', 'blank')",
    "    ns   = float(config.get('note_font_size', 8))\n    ls   = float(config.get('line_spacing', 0))\n    tmpl = g.get('template', 'blank')",
    'page_block add ls')

# 5. snap_thresh: use (fs+ls)
s = _p(s,
    '    snap_thresh = fs * snap_chars',
    '    snap_thresh = (fs + ls) * snap_chars',
    'snap_thresh fix')

# 6. inject ocr_y_min before raw_dy loop
s = _p(s,
    "    raw_dy: list[float] = []\n    for col in recs:",
    "    all_y1 = [_px_to_pt(col['chars'][0].bbox[1], dpi) for col in recs if col['chars']]\n    ocr_y_min = min(all_y1) if all_y1 else 0.0\n    raw_dy: list[float] = []\n    for col in recs:",
    'inject ocr_y_min')

# 7. dy: relative to ocr_y_min (not tian_tou)
s = _p(s,
    '            raw_dy.append(y1_pt - tian_tou)',
    '            raw_dy.append(y1_pt - ocr_y_min)',
    'dy relative to ocr_y_min')

# 8. fix x_left: OCR-range normalised
_old_xl = ("        # x_left: OCR cx \u6620\u5c04\u5230\u7248\u5fc3\u5bbd\u5ea6\n"
           "        right_off = (page.orig_width_px - cx_px) / page.orig_width_px * banxin_w\n"
           "        x_left    = banxin_w - right_off - fw_val / 2")
_new_xl = ("        # x_left: OCR \u5217 cx \u5728\u6587\u5b57\u533a\u57df\u5185\u5f52\u4e00\u5316\u2192\u7248\u5fc3\n"
           "        _acx = [r['col_cx_px'] for r in recs]\n"
           "        _xmin = min(_acx); _xmax = max(_acx); _xrng = max(_xmax-_xmin, 1.0)\n"
           "        x_left = (cx_px - _xmin) / _xrng * (banxin_w - fw_val)")
s = _p(s, _old_xl, _new_xl, 'fix x_left')

# 9. fix h_pt: include line_spacing
s = _p(s,
    '        h_pt    = n * fw_val',
    '        h_pt    = n * (fw_val + ls)',
    'fix h_pt')

p.write_text(s, encoding='utf-8', newline='\r\n')
print('\ntypst_writer.py patched successfully')
