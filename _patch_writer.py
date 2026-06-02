"""Fix: char_spacing default to standard publishing line gap (20% of font size)."""
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

# ── Fix 1: _build_header — ls 默认改为字号20%（标准出版行距）──────
# 原: ls = float(config.get('line_spacing', 0))
# 新: 读出原始值，若<=0则自动取 fs*0.20（标准行间距约为字号20%）
s = pat(s,
    "    fs  = float(config.get('font_size', 12))\n"
    "    ns  = float(config.get('note_font_size', 8))\n"
    "    ls  = float(config.get('line_spacing', 0))\n"
    "    g   = config.get('guji_layout', {})",
    "    fs  = float(config.get('font_size', 12))\n"
    "    ns  = float(config.get('note_font_size', 8))\n"
    "    _ls_raw = float(config.get('line_spacing', 0))\n"
    "    ls  = _ls_raw if _ls_raw > 0 else round(fs * 0.20, 2)  # 默认=字号20%（标准行距）\n"
    "    g   = config.get('guji_layout', {})",
    '_build_header ls default')

# ── Fix 2: _build_page_block — 同样处理 ls 默认值 ─────────────────
s = pat(s,
    "    ls          = float(config.get('line_spacing', 0))\n"
    "    col_spacing = float(config.get('column_spacing', 4))",
    "    _ls_raw     = float(config.get('line_spacing', 0))\n"
    "    ls          = _ls_raw if _ls_raw > 0 else round(fs * 0.20, 2)  # 默认=字号20%\n"
    "    col_spacing = float(config.get('column_spacing', 4))",
    '_build_page_block ls default')

# ── Fix 3: 生成的 Typst 注释说明 cs 的含义 ────────────────────────
s = pat(s,
    "        f'#let cs = {ls:.2f}pt  // char_spacing',",
    "        f'#let cs = {ls:.2f}pt  // char_spacing (line_spacing={_ls_raw}; 0=auto 20% of font)',",
    'cs comment')

p.write_text(s, encoding='utf-8', newline='\r\n')
print('Done')
