"""Write a minimal test.typ to isolate the blank-page issue."""
import pathlib

# 极简测试：只保留最核心的部分，用固定值替换所有变量
test1 = r"""// test1: 最简 vcol，无变量引用
#let vcol(s) = {
  stack(dir: ttb,
    ..s.clusters().map(c =>
      box(width: 14pt, height: 16.8pt)[#align(center + horizon)[#c]]
    )
  )
}

#block(width: 400pt, height: 500pt)[
  #place(top + left, dx: 100pt, dy: 0pt, vcol("周易玩辭"))
]
"""

# 测试2：加入 cs_r 变量
test2 = r"""// test2: 带 cs_r 变量
#let cw   = 14pt
#let cs_r = 0.2

#let vcol(s, fw: cw) = {
  stack(dir: ttb,
    ..s.clusters().map(c =>
      box(width: fw, height: fw * (1 + cs_r))[#align(center + horizon)[#text(size: fw)[#c]]]
    )
  )
}

#block(width: 400pt, height: 500pt)[
  #place(top + left, dx: 100pt, dy: 0pt, vcol("周易玩辭"))
]
"""

# 测试3：加入所有 let 变量
test3 = r"""// test3: 带所有变量但无中文注释
#let cw          = 14.00pt
#let heading_fw  = 21.00pt
#let title_fw    = 18.20pt
#let subtitle_fw = 14.00pt
#let author_fw   = 11.20pt
#let interp_fw   = 11.20pt
#let note_fw     = 7.56pt
#let ns          = 7.56pt
#let pagenum_fw  = 9.80pt
#let cs_r        = 0.2000

#let vcol(s, fw: cw) = {
  stack(dir: ttb,
    ..s.clusters().map(c =>
      box(width: fw, height: fw * (1 + cs_r))
        [#align(center + horizon)[#text(size: fw)[#c]]]
    )
  )
}

#let vmain(s)     = vcol(s, fw: cw)
#let vheading(s)  = vcol(s, fw: heading_fw)
#let vtitle(s)    = vcol(s, fw: title_fw)
#let vsubtitle(s) = vcol(s, fw: subtitle_fw)
#let vauthor(s)   = vcol(s, fw: author_fw)
#let vinterp(s)   = vcol(s, fw: interp_fw)
#let vnote(s)     = vcol(s, fw: note_fw)

#block(width: 400pt, height: 500pt)[
  #place(top + left, dx: 100pt, dy: 0pt, box(width: cw, height: 50.4pt)[#vcol("國立正", fw: cw)])
  #place(top + left, dx: 80pt,  dy: 0pt, box(width: cw, height: 134.4pt)[#vcol("周易玩辭叙", fw: cw)])
]
"""

out = pathlib.Path('output')
pathlib.Path(out / 'test1.typ').write_text(test1, encoding='utf-8', newline='\r\n')
pathlib.Path(out / 'test2.typ').write_text(test2, encoding='utf-8', newline='\r\n')
pathlib.Path(out / 'test3.typ').write_text(test3, encoding='utf-8', newline='\r\n')
print('Written: output/test1.typ  test2.typ  test3.typ')
print()
print('请在 Tinymist 中依次打开三个文件，找到最小复现步骤。')
