"""Fix: (1) column x_left use fixed spacing, (2) remove trailing blank page."""
import pathlib, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

p = pathlib.Path('modules/typst_writer.py')
s = p.read_text(encoding='utf-8')

def pat(s, old, new, tag):
    if old in s:
        print(f'  OK: {tag}')
        return s.replace(old, new, 1)
    print(f'  MISS: {tag}')
    print(f'  expected: {old!r}')
    return s

# ── Fix A: 在 _build_page_block 读取 col_spacing ──────────────────
s = pat(s,
    "    ls   = float(config.get('line_spacing', 0))\n    tmpl = g.get('template', 'blank')",
    "    ls          = float(config.get('line_spacing', 0))\n    col_spacing = float(config.get('column_spacing', 4))\n    tmpl = g.get('template', 'blank')",
    'read col_spacing')

# ── Fix B: x_left 改为固定步长从右到左 ────────────────────────────
s = pat(s,
    "        # x_left: OCR \u5217 cx \u5728\u6587\u5b57\u533a\u57df\u5185\u5f52\u4e00\u5316\u2192\u7248\u5fc3\n        _acx = [r['col_cx_px'] for r in recs]\n        _xmin = min(_acx); _xmax = max(_acx); _xrng = max(_xmax-_xmin, 1.0)\n        x_left = (cx_px - _xmin) / _xrng * (banxin_w - fw_val)",
    "        # x_left: \u4ece\u7248\u5fc3\u53f3\u8fb9\u8d77\uff0c\u6309 source_order \u56fa\u5b9a\u6b65\u957f(fw+col_spacing)\u4ece\u53f3\u5230\u5de6\u6392\u5217\n        col_step = fw_val + col_spacing\n        x_left   = banxin_w - fw_val - (order - 1) * col_step",
    'x_left fixed step')

# ── Fix C: 去掉页块末尾的空行（防止 Typst 产生空白页）─────────────
s = pat(s,
    "    lns.append(']')\n    lns.append('')",
    "    lns.append(']')",
    'remove trailing blank line')

p.write_text(s, encoding='utf-8', newline='\r\n')

# ── Fix D: 统一步长用正文字号 fs，保证 note 列不错位 ──────────────
s2 = p.read_text(encoding='utf-8')
old_d = ("        # x_left: \u4ece\u7248\u5fc3\u53f3\u8fb9\u8d77\uff0c\u6309 source_order \u56fa\u5b9a\u6b65\u957f(fw+col_spacing)\u4ece\u53f3\u5230\u5de6\u6392\u5217\n"
         "        col_step = fw_val + col_spacing\n"
         "        x_left   = banxin_w - fw_val - (order - 1) * col_step")
new_d = ("        # x_left: \u4ece\u7248\u5fc3\u53f3\u8fb9\u8d77\uff0c\u6309 source_order \u56fa\u5b9a\u6b65\u957f\u4ece\u53f3\u5230\u5de6\u6392\u5217\n"
         "        col_step = fs + col_spacing      # \u7edf\u4e00\u7528\u6b63\u6587\u5b57\u53f7\uff0c\u4fdd\u8bc1 note \u5217\u4e0d\u9519\u4f4d\n"
         "        x_left   = banxin_w - fw_val - (order - 1) * col_step")
if old_d in s2:
    s2 = s2.replace(old_d, new_d, 1)
    p.write_text(s2, encoding='utf-8', newline='\r\n')
    print('  OK: unify col_step to fs')
else:
    print('  MISS fix D')

print('Done')

