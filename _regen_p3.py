import json, sys, pathlib
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

# 确保 font_size=11 写入配置
_cfg_path = pathlib.Path('config/layout_config.yaml')
_cfg_text = _cfg_path.read_text(encoding='utf-8')
if 'font_size: 12\n' in _cfg_text:
    _cfg_path.write_text(_cfg_text.replace('font_size: 12\n', 'font_size: 11\n'), encoding='utf-8')
    print('>> font_size patched to 11')

from modules.page_model import PageData, TextColumn, CharData
from modules.typst_writer import create_typst, _mm_to_pt
from modules.pdf_writer import load_config

cfg  = load_config('config/layout_config.yaml')
data = json.load(open('output/ocr_cache_zywc_p1-20.json', encoding='utf-8'))
pd   = next(p for p in data if p['page_num'] == 3)
cols = [TextColumn(bbox=tuple(c['col_bbox']),
                   chars=[CharData(text=ch['text'], bbox=tuple(ch['bbox']),
                                   confidence=ch['conf']) for ch in c['chars']])
        for c in pd['text_columns']]
pages = [PageData(page_num=pd['page_num'], orig_width_px=pd['width_px'],
                  orig_height_px=pd['height_px'], dpi=pd['dpi'], text_columns=cols)]
create_typst(pages, 'output/debug_p3.typ', cfg)

g  = cfg.get('guji_layout', {})
fs = float(cfg.get('font_size', 11))
bw = 182 - float(g['zhuang_ding_mm']) - float(g['shu_kou_mm'])
bh = 257 - float(g['tian_tou_mm'])    - float(g['di_jiao_mm'])
print(f"字号={fs}pt  注={cfg.get('note_font_size')}pt  列间距={cfg.get('column_spacing')}pt")
print(f"天头={g['tian_tou_mm']}mm  地脚={g['di_jiao_mm']}mm  装订={g['zhuang_ding_mm']}mm  书口={g['shu_kou_mm']}mm")
print(f"版心={bw}mm x {bh}mm  ({_mm_to_pt(bw):.0f}pt x {_mm_to_pt(bh):.0f}pt)")
print()
print(pathlib.Path('output/debug_p3.typ').read_text(encoding='utf-8'))

print(f"版心: {bw}mm x {bh}mm = {_mm_to_pt(bw):.0f}pt x {_mm_to_pt(bh):.0f}pt")
print()
print(pathlib.Path('output/debug_p3.typ').read_text(encoding='utf-8'))
