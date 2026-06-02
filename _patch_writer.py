"""Fix README: replace main/title/note etc. with vmain/vtitle/vnote."""
import pathlib, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

rp = pathlib.Path('README.md')
s = rp.read_text(encoding='utf-8')

replacements = [
    ('#main("…")',      '#vmain("…")'),
    ('#heading("…")',   '#vheading("…")'),
    ('#title("…")',     '#vtitle("…")'),
    ('#subtitle("…")',  '#vsubtitle("…")'),
    ('#author("…")',    '#vauthor("…")'),
    ('#interp("…")',    '#vinterp("…")'),
    ('#note("…")',      '#vnote("…")'),
    ('#main("正文文字")',  '#vmain("正文文字")'),
    ('#title("標題")',   '#vtitle("標題")'),
    ('#note("夾注")',    '#vnote("夾注")'),
    ('#main("…")  #title("…")  #note("…")',
     '#vmain("…")  #vtitle("…")  #vnote("…")'),
    ('#title("周易玩辭")',   '#vtitle("周易玩辭")'),
    ('#heading("周易玩辭")', '#vheading("周易玩辭")'),
    ('#note("玩辭")',         '#vnote("玩辭")'),
    ('#let main(s)',    '#let vmain(s)'),
    ('#let heading(s)', '#let vheading(s)'),
    ('#let title(s)',   '#let vtitle(s)'),
    ('#let subtitle(s)','#let vsubtitle(s)'),
    ('#let author(s)',  '#let vauthor(s)'),
    ('#let interp(s)',  '#let vinterp(s)'),
    ('#let note(s)',    '#let vnote(s)'),
]

for old, new in replacements:
    if old in s:
        s = s.replace(old, new)
        print(f'  OK: {old[:35]}')

rp.write_text(s, encoding='utf-8', newline='\r\n')
print('README updated')
