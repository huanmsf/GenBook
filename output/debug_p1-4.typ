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

// === 第 1 页  blank  重分列=17列  原PDF=553x930pt  版心=431x530pt  装订=右→左 ===

// 版心 block（含页码绝对定位）
#block(width: 430.9pt, height: 530.1pt)[
  #place(bottom + center)[一]
  // 列 1: main   字数=  2  cx=2226px  x_left=416.9pt  dy=827.8pt
  #place(top + left, dx: 416.9pt, dy: 827.8pt, box(width: cw, height: 33.6pt)[#vcol("19", fw: cw)])
  // 列 2: main   字数=  2  cx=2106px  x_left=397.9pt  dy=827.8pt
  #place(top + left, dx: 397.9pt, dy: 827.8pt, box(width: cw, height: 33.6pt)[#vcol("18", fw: cw)])
  // 列 3: main   字数=  2  cx=1978px  x_left=378.9pt  dy=827.8pt
  #place(top + left, dx: 378.9pt, dy: 827.8pt, box(width: cw, height: 33.6pt)[#vcol("17", fw: cw)])
  // 列 4: main   字数=  2  cx=1864px  x_left=359.9pt  dy=827.8pt
  #place(top + left, dx: 359.9pt, dy: 827.8pt, box(width: cw, height: 33.6pt)[#vcol("16", fw: cw)])
  // 列 5: main   字数=  2  cx=1746px  x_left=340.9pt  dy=827.8pt
  #place(top + left, dx: 340.9pt, dy: 827.8pt, box(width: cw, height: 33.6pt)[#vcol("15", fw: cw)])
  // 列 6: main   字数=  2  cx=1620px  x_left=321.9pt  dy=827.8pt
  #place(top + left, dx: 321.9pt, dy: 827.8pt, box(width: cw, height: 33.6pt)[#vcol("14", fw: cw)])
  // 列 7: main   字数=  2  cx=1502px  x_left=302.9pt  dy=827.8pt
  #place(top + left, dx: 302.9pt, dy: 827.8pt, box(width: cw, height: 33.6pt)[#vcol("13", fw: cw)])
  // 列 8: main   字数=  2  cx=1385px  x_left=283.9pt  dy=827.8pt
  #place(top + left, dx: 283.9pt, dy: 827.8pt, box(width: cw, height: 33.6pt)[#vcol("12", fw: cw)])
  // 列 9: main   字数=  2  cx=1148px  x_left=264.9pt  dy=827.8pt
  #place(top + left, dx: 264.9pt, dy: 827.8pt, box(width: cw, height: 33.6pt)[#vcol("10", fw: cw)])
  // 列10: main   字数=  1  cx=778px  x_left=245.9pt  dy=827.8pt
  #place(top + left, dx: 245.9pt, dy: 827.8pt, box(width: cw, height: 16.8pt)[#vcol("7", fw: cw)])
  // 列11: main   字数=  1  cx=659px  x_left=226.9pt  dy=827.8pt
  #place(top + left, dx: 226.9pt, dy: 827.8pt, box(width: cw, height: 16.8pt)[#vcol("6", fw: cw)])
  // 列12: main   字数=  1  cx=542px  x_left=207.9pt  dy=827.8pt
  #place(top + left, dx: 207.9pt, dy: 827.8pt, box(width: cw, height: 16.8pt)[#vcol("5", fw: cw)])
  // 列13: main   字数=  1  cx=422px  x_left=188.9pt  dy=827.8pt
  #place(top + left, dx: 188.9pt, dy: 827.8pt, box(width: cw, height: 16.8pt)[#vcol("4", fw: cw)])
  // 列14: main   字数=  4  cx=341px  x_left=169.9pt  dy=0.0pt
  #place(top + left, dx: 169.9pt, dy: 0.0pt, box(width: cw, height: 67.2pt)[#vcol("周易玩辭", fw: cw)])
  // 列15: main   字数=  1  cx=304px  x_left=150.9pt  dy=827.8pt
  #place(top + left, dx: 150.9pt, dy: 827.8pt, box(width: cw, height: 16.8pt)[#vcol("3", fw: cw)])
  // 列16: main   字数=  1  cx=185px  x_left=131.9pt  dy=827.8pt
  #place(top + left, dx: 131.9pt, dy: 827.8pt, box(width: cw, height: 16.8pt)[#vcol("2", fw: cw)])
  // 列17: main   字数=  4  cx=34px  x_left=112.9pt  dy=827.8pt
  #place(top + left, dx: 112.9pt, dy: 827.8pt, box(width: cw, height: 67.2pt)[#vcol("ches", fw: cw)])
]
#pagebreak()

// === 第 2 页  blank  重分列=0列  原PDF=479x872pt  版心=431x530pt  装订=左→右 ===

#place(bottom + center)[二]
#v(530.1pt)
#pagebreak()

// === 第 3 页  blank  重分列=12列  原PDF=479x872pt  版心=431x530pt  装订=右→左 ===

// 版心 block（含页码绝对定位）
#block(width: 430.9pt, height: 530.1pt)[
  #place(bottom + center)[三]
  // 列 1: main   字数=  3  cx=1848px  x_left=416.9pt  dy=185.5pt
  #place(top + left, dx: 416.9pt, dy: 185.5pt, box(width: cw, height: 50.4pt)[#vcol("國立正", fw: cw)])
  // 列 2: main   字数=  8  cx=1774px  x_left=397.9pt  dy=0.0pt
  #place(top + left, dx: 397.9pt, dy: 0.0pt, box(width: cw, height: 134.4pt)[#vcol("周易玩辭叙平圖書", fw: cw)])
  // 列 3: main   字数=  3  cx=1700px  x_left=378.9pt  dy=185.5pt
  #place(top + left, dx: 378.9pt, dy: 185.5pt, box(width: cw, height: 50.4pt)[#vcol("馆收藏", fw: cw)])
  // 列 4: main   字数= 20  cx=1588px  x_left=359.9pt  dy=0.0pt
  #place(top + left, dx: 359.9pt, dy: 0.0pt, box(width: cw, height: 336.0pt)[#vcol("叙曰大傳曰君子居則觀其象而玩其辭動則觀其", fw: cw)])
  // 列 5: main   字数= 20  cx=1405px  x_left=340.9pt  dy=0.0pt
  #place(top + left, dx: 340.9pt, dy: 0.0pt, box(width: cw, height: 336.0pt)[#vcol("變而玩其占讀易之法盡於此矣易之道四其實則", fw: cw)])
  // 列 6: main   字数= 20  cx=1226px  x_left=321.9pt  dy=0.0pt
  #place(top + left, dx: 321.9pt, dy: 0.0pt, box(width: cw, height: 336.0pt)[#vcol("二象與辭是也變則象之進退也占則辭之吉凶也", fw: cw)])
  // 列 7: main   字数= 20  cx=1042px  x_left=302.9pt  dy=0.0pt
  #place(top + left, dx: 302.9pt, dy: 0.0pt, box(width: cw, height: 336.0pt)[#vcol("不識其象何以知其變不通其辭何以决其占然而", fw: cw)])
  // 列 8: main   字数= 20  cx=860px  x_left=283.9pt  dy=0.0pt
  #place(top + left, dx: 283.9pt, dy: 0.0pt, box(width: cw, height: 336.0pt)[#vcol("聖人因象以措辭後學因辭而測象則今之讀易所", fw: cw)])
  // 列 9: main   字数= 20  cx=677px  x_left=264.9pt  dy=0.0pt
  #place(top + left, dx: 264.9pt, dy: 0.0pt, box(width: cw, height: 336.0pt)[#vcol("當反復紬繹精思而深味者莫辭若也於是作周易", fw: cw)])
  // 列10: main   字数=  2  cx=500px  x_left=245.9pt  dy=0.0pt
  #place(top + left, dx: 245.9pt, dy: 0.0pt, box(width: cw, height: 33.6pt)[#vcol("玩辭", fw: cw)])
  // 列11: main   字数= 20  cx=320px  x_left=226.9pt  dy=0.0pt
  #place(top + left, dx: 226.9pt, dy: 0.0pt, box(width: cw, height: 336.0pt)[#vcol("皇宋慶元四年歲次戊午秋九月己未江陵項盎述", fw: cw)])
  // 列12: main   字数=  6  cx=142px  x_left=207.9pt  dy=112.3pt
  #place(top + left, dx: 207.9pt, dy: 112.3pt, box(width: cw, height: 100.8pt)[#vcol("周易上篇六卷", fw: cw)])
]
#pagebreak()

// === 第 4 页  blank  重分列=10列  原PDF=480x874pt  版心=431x530pt  装订=左→右 ===

// 版心 block（含页码绝对定位）
#block(width: 430.9pt, height: 530.1pt)[
  #place(bottom + center)[四]
  // 列 1: main   字数=  6  cx=1845px  x_left=416.9pt  dy=61.2pt
  #place(top + left, dx: 416.9pt, dy: 61.2pt, box(width: cw, height: 100.8pt)[#vcol("周易下篇六卷", fw: cw)])
  // 列 2: main   字数=  4  cx=1661px  x_left=397.9pt  dy=61.2pt
  #place(top + left, dx: 397.9pt, dy: 61.2pt, box(width: cw, height: 67.2pt)[#vcol("繫辭兩卷", fw: cw)])
  // 列 3: main   字数=  4  cx=1479px  x_left=378.9pt  dy=61.2pt
  #place(top + left, dx: 378.9pt, dy: 61.2pt, box(width: cw, height: 67.2pt)[#vcol("說卦一卷", fw: cw)])
  // 列 4: main   字数=  6  cx=1299px  x_left=359.9pt  dy=61.2pt
  #place(top + left, dx: 359.9pt, dy: 61.2pt, box(width: cw, height: 100.8pt)[#vcol("序卦雜卦一卷", fw: cw)])
  // 列 5: main   字数= 18  cx=1114px  x_left=340.9pt  dy=0.0pt
  #place(top + left, dx: 340.9pt, dy: 0.0pt, box(width: cw, height: 302.4pt)[#vcol("嘉泰二年壬戍之秋重修周易玩辭十六卷章", fw: cw)])
  // 列 6: main   字数= 18  cx=936px  x_left=321.9pt  dy=0.0pt
  #place(top + left, dx: 321.9pt, dy: 0.0pt, box(width: cw, height: 302.4pt)[#vcol("句粗定因自嘆曰安丗之所學蓋伊川程子之", fw: cw)])
  // 列 7: main   字数= 18  cx=760px  x_left=302.9pt  dy=0.0pt
  #place(top + left, dx: 302.9pt, dy: 0.0pt, box(width: cw, height: 302.4pt)[#vcol("書也程子平生所著獨易傳爲全書安丗受而", fw: cw)])
  // 列 8: main   字数= 18  cx=576px  x_left=283.9pt  dy=0.0pt
  #place(top + left, dx: 283.9pt, dy: 0.0pt, box(width: cw, height: 302.4pt)[#vcol("讀之三十年矣今以其所得於易傳者述爲此", fw: cw)])
  // 列 9: main   字数= 18  cx=394px  x_left=264.9pt  dy=0.0pt
  #place(top + left, dx: 264.9pt, dy: 0.0pt, box(width: cw, height: 302.4pt)[#vcol("書而其文無與易傳合者合則無用述此書矣", fw: cw)])
  // 列10: main   字数= 18  cx=216px  x_left=245.9pt  dy=0.0pt
  #place(top + left, dx: 245.9pt, dy: 0.0pt, box(width: cw, height: 302.4pt)[#vcol("丗之友朋以易傳之理觀吾書則本末條貫無", fw: cw)])
]