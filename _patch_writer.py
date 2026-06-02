"""Fix two blank-page causes in typst_writer.py:
  1. dy clamp: cap dy_pt so box never overflows banxin_h
  2. 0-col page: use #block instead of #place+#v to avoid stray space
"""
import pathlib

p = pathlib.Path('modules/typst_writer.py')
src = p.read_text(encoding='utf-8')
orig = src

# ── Fix 1: clamp dy so content never overflows banxin ──────────────────────
old_dy = "        # dy: snap 后的版心顶偏移\n        dy_pt = snapped_dy[ci] if raw_dy else 0.0"
new_dy = (
    "        # dy: snap 后的版心顶偏移，clamp 确保 box 不超出版心底部\n"
    "        dy_pt = snapped_dy[ci] if raw_dy else 0.0\n"
    "        dy_pt = max(0.0, min(dy_pt, banxin_h - h_pt))"
)
src = src.replace(old_dy, new_dy)

# ── Fix 2: 0-col page use #block so it exactly occupies one page ───────────
old_empty = (
    "    # 空白页（无任何列）：用 #v 撑高度 + 页码，避免 #block 导致的双空白页\n"
    "    if not recs:\n"
    "        if show_num:\n"
    "            lns.append(f'#place(bottom + center)[#text(size: pagenum_fw)[{num}]]')\n"
    "        lns.append(f'#v({banxin_h:.1f}pt)')\n"
    "        return '\\n'.join(lns)"
)
new_empty = (
    "    # 空白页（无任何列）：用 #block 精确占满一页，#place 放页码\n"
    "    if not recs:\n"
    "        lns.append(f'#block(width: {banxin_w:.1f}pt, height: {banxin_h:.1f}pt)[')\n"
    "        if show_num:\n"
    "            lns.append(f'  #place(bottom + center)[#text(size: pagenum_fw)[{num}]]')\n"
    "        lns.append(']')\n"
    "        return '\\n'.join(lns)"
)
src = src.replace(old_empty, new_empty)

checks = [
    ('dy clamp',           'min(dy_pt, banxin_h - h_pt)' in src),
    ('0-col uses #block',  "空白页（无任何列）：用 #block 精确占满一页" in src),
    ('no bare #v',         "#v({banxin_h" not in src),
]
all_ok = True
for name, ok in checks:
    print(f'  [{"OK" if ok else "FAIL"}] {name}')
    if not ok: all_ok = False

if all_ok:
    p.write_text(src, encoding='utf-8', newline='\r\n')
    print('\nOK: typst_writer.py patched')
else:
    print('\nERROR: patch failed – file NOT written')
