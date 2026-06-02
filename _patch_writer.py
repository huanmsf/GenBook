"""Regenerate debug_p1-4.typ and show key lines."""
import json, sys, pathlib
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from modules.page_model import PageData, TextColumn, CharData
from modules.typst_writer import create_typst
from modules.pdf_writer import load_config

cfg  = load_config('config/layout_config.yaml')
data = json.load(open('output/ocr_cache_zywc_p1-20.json', encoding='utf-8'))
pages = []
for pd in sorted(data, key=lambda x: x['page_num'])[:4]:
    cols = [TextColumn(bbox=tuple(c['col_bbox']),
                       chars=[CharData(text=ch['text'], bbox=tuple(ch['bbox']),
                                       confidence=ch['conf']) for ch in c['chars']])
            for c in pd['text_columns']]
    pages.append(PageData(page_num=pd['page_num'], orig_width_px=pd['width_px'],
                          orig_height_px=pd['height_px'], dpi=pd['dpi'], text_columns=cols))
create_typst(pages, 'output/debug_p1-4.typ', cfg)
s = pathlib.Path('output/debug_p1-4.typ').read_text(encoding='utf-8')
print('Generated. Key lines:')
for i, line in enumerate(s.splitlines(), 1):
    if any(x in line for x in ['#block', '#v(', '#pagebreak', '===']):
        print(f'  {i:>4}: {line}')
