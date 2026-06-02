// test2: 带 cs_r 变量
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
