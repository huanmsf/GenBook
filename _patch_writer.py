import pathlib, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p = pathlib.Path('README.md')
s = p.read_text(encoding='utf-8')
old = '7. [正文 / 注文 / 标题调整指南](#7-正文--注文--标题调整指南)'
new = '7. [版面元素样式系统](#7-版面元素样式系统)'
if old in s:
    p.write_text(s.replace(old, new, 1), encoding='utf-8', newline='\r\n')
    print('OK: TOC updated')
else:
    print('MISS, checking what is in TOC:')
    for l in s.splitlines():
        if '正文' in l or '版面' in l or '. [' in l:
            print(' ', l)
