"""Fix: vcol uses text(size: fw) so note columns render at ns pt, not 14pt."""
import pathlib, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

p = pathlib.Path('modules/typst_writer.py')
s = p.read_text(encoding='utf-8')

def pat(s, old, new, tag):
    if old in s:
        print(f'  OK: {tag}')
        return s.replace(old, new, 1)
    print(f'  MISS: {tag}')
    return s

# ── Fix: vcol 内每个字加 text(size: fw) ────────────────────────────
# 原：box(width: fw, height: fw + cs)[#align(center + horizon)[#c]]
# 新：box(width: fw, height: fw + cs)[#align(center + horizon)[#text(size: fw)[#c]]]
# 这样 note 列传入 fw=ns=7.5pt 时字号也变为 7.5pt
s = pat(s,
    '      box(width: fw, height: fw + cs)[#align(center + horizon)[#c]]',
    '      box(width: fw, height: fw + cs)[#align(center + horizon)[#text(size: fw)[#c]]]',
    'vcol text size follows fw')

# ── 同步修正 cs 计算：note 列的行距应按 ns 算，正文列按 fs 算 ──────
# cs 目前是全局的，统一按 fs*20%，但 note 列字号是 ns，cs 对 note 显得偏大
# 方案：在 vcol 内用 cs 比例而不是绝对值——改为相对行距 cs_ratio
# 具体：把 #let cs = Xpt 改为比例，vcol 里用 fw * cs_ratio
# 但为简单起见，改用两个变量：cs_main 和 cs_note
s = pat(s,
    "        f'#let cs = {ls:.2f}pt  // char_spacing (line_spacing={_ls_raw}; 0=auto 20% of font)',",
    "        f'#let cs_r = {ls/fs:.4f}  // char_spacing ratio (={ls:.2f}pt / {fs:.1f}pt)',",
    'cs to ratio')

# vcol 里从 fw + cs 改为 fw * (1 + cs_r)，这样 note 列行距按 ns 比例算
s = pat(s,
    '      box(width: fw, height: fw + cs)[#align(center + horizon)[#text(size: fw)[#c]]]',
    '      box(width: fw, height: fw * (1 + cs_r))[#align(center + horizon)[#text(size: fw)[#c]]]',
    'box height uses fw * ratio')

# ── h_pt 也要改为用 ratio ──────────────────────────────────────────
# 原：h_pt = n * (fw_val + ls)
# 新：h_pt = n * fw_val * (1 + ls/fs)  但要用 ls_ratio
s = pat(s,
    '        h_pt    = n * (fw_val + ls)',
    '        ls_ratio = ls / fs  # 相对行距比例\n        h_pt    = n * fw_val * (1 + ls_ratio)',
    'h_pt uses ratio')

p.write_text(s, encoding='utf-8', newline='\r\n')
print('Done')
