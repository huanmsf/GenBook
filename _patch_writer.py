import pathlib

p = pathlib.Path('modules/typst_writer.py')
txt = p.read_text(encoding='utf-8')

q = "'"
old1 = f"            lns.append(f{q}#place(bottom + center)[{{num}}]{q})"
new1 = f"            lns.append(f{q}#place(bottom + center)[#text(size: pagenum_fw)[{{num}}]]{q})"
old2 = f"    lns.append(f{q}  #place(bottom + center)[{{num}}]{q})"
new2 = f"    lns.append(f{q}  #place(bottom + center)[#text(size: pagenum_fw)[{{num}}]]{q})"

txt2 = txt.replace(old1, new1).replace(old2, new2)
if txt2 == txt:
    print('ERROR: no replacement made')
else:
    p.write_text(txt2, encoding='utf-8', newline='\r\n')
    print('OK: pagenum_fw applied to both page-num placements')
