// test1: 最简 vcol，无变量引用
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
