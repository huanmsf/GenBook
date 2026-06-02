// test3: 带所有变量但无中文注释
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
