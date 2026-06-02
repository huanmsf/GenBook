// GenBook v9 — 字符坐标重分列 + place 绝对定位竖排
// 模板：blank

#set text(
  font: ("STKaiTi", "Noto Serif CJK TC", "SimSun"),
  size: 14.0pt,
  lang: "zh"
)
#set par(leading: 0pt, spacing: 0pt)
#let cw = 14.0pt
#let ns = 7.5pt
#let cs_r = 0.2000  // char_spacing ratio (=2.80pt / 14.0pt)
#set page(
  paper: "jis-b5",
  margin: (top: 113.4pt, bottom: 85.0pt,
           left: 56.7pt, right: 28.3pt)
)

// vcol: 逐字竖排 — stack(dir: ttb) 保证从上到下
#let vcol(s, fw: cw) = {
  stack(dir: ttb,
    ..s.clusters().map(c =>
      box(width: fw, height: fw * (1 + cs_r))[#align(center + horizon)[#text(size: fw)[#c]]]
    )
  )
}

// === 第 3 页  blank  重分列=12列  原PDF=479x872pt  版心=394x674pt  装订=右→左 ===

// 版心 block（含页码绝对定位）
#block(width: 393.5pt, height: 674.0pt)[
  #place(bottom + center)[三]
  // 列 1: title  字数=  3  cx=1848px  x_left=379.5pt  dy=185.5pt
  #place(top + left, dx: 379.5pt, dy: 185.5pt, box(width: cw, height: 50.4pt)[#vcol("國立正", fw: cw)])
  // 列 2: note   字数=  8  cx=1774px  x_left=367.0pt  dy=0.0pt
  #place(top + left, dx: 367.0pt, dy: 0.0pt, box(width: ns, height: 72.0pt)[#vcol("周易玩辭叙平圖書", fw: ns)])
  // 列 3: title  字数=  3  cx=1700px  x_left=341.5pt  dy=185.5pt
  #place(top + left, dx: 341.5pt, dy: 185.5pt, box(width: cw, height: 50.4pt)[#vcol("馆收藏", fw: cw)])
  // 列 4: main   字数= 20  cx=1588px  x_left=322.5pt  dy=0.0pt
  #place(top + left, dx: 322.5pt, dy: 0.0pt, box(width: cw, height: 336.0pt)[#vcol("叙曰大傳曰君子居則觀其象而玩其辭動則觀其", fw: cw)])
  // 列 5: main   字数= 20  cx=1405px  x_left=303.5pt  dy=0.0pt
  #place(top + left, dx: 303.5pt, dy: 0.0pt, box(width: cw, height: 336.0pt)[#vcol("變而玩其占讀易之法盡於此矣易之道四其實則", fw: cw)])
  // 列 6: main   字数= 20  cx=1226px  x_left=284.5pt  dy=0.0pt
  #place(top + left, dx: 284.5pt, dy: 0.0pt, box(width: cw, height: 336.0pt)[#vcol("二象與辭是也變則象之進退也占則辭之吉凶也", fw: cw)])
  // 列 7: main   字数= 20  cx=1042px  x_left=265.5pt  dy=0.0pt
  #place(top + left, dx: 265.5pt, dy: 0.0pt, box(width: cw, height: 336.0pt)[#vcol("不識其象何以知其變不通其辭何以决其占然而", fw: cw)])
  // 列 8: main   字数= 20  cx=860px  x_left=246.5pt  dy=0.0pt
  #place(top + left, dx: 246.5pt, dy: 0.0pt, box(width: cw, height: 336.0pt)[#vcol("聖人因象以措辭後學因辭而測象則今之讀易所", fw: cw)])
  // 列 9: main   字数= 20  cx=677px  x_left=227.5pt  dy=0.0pt
  #place(top + left, dx: 227.5pt, dy: 0.0pt, box(width: cw, height: 336.0pt)[#vcol("當反復紬繹精思而深味者莫辭若也於是作周易", fw: cw)])
  // 列10: title  字数=  2  cx=500px  x_left=208.5pt  dy=0.0pt
  #place(top + left, dx: 208.5pt, dy: 0.0pt, box(width: cw, height: 33.6pt)[#vcol("玩辭", fw: cw)])
  // 列11: main   字数= 20  cx=320px  x_left=189.5pt  dy=0.0pt
  #place(top + left, dx: 189.5pt, dy: 0.0pt, box(width: cw, height: 336.0pt)[#vcol("皇宋慶元四年歲次戊午秋九月己未江陵項盎述", fw: cw)])
  // 列12: title  字数=  6  cx=142px  x_left=170.5pt  dy=112.3pt
  #place(top + left, dx: 170.5pt, dy: 112.3pt, box(width: cw, height: 100.8pt)[#vcol("周易上篇六卷", fw: cw)])
]