// GenBook v9 — 字符坐标重分列 + place 绝对定位竖排
// 模板：blank  正文:14.0pt  纸张:jis-b5

// ── 全局文字设置 ─────────────────────────────────────
#set text(
  font: ("STKaiTi", "Noto Serif CJK TC", "SimSun"),
  size: 14.0pt,
  lang: "zh"
)
#set par(leading: 0pt, spacing: 0pt)

// ── 纸张与版心 ───────────────────────────────────────
#set page(
  paper: "jis-b5",
  margin: (top: 113.4pt, bottom: 85.0pt,
           left: 56.7pt, right: 28.3pt)
)

// ── 字号变量（修改 config/layout_config.yaml → styles 节即可）──
#let cw          = 14.00pt   // 正文 main（基准字号）
#let heading_fw  = 21.00pt   // 大標題 heading（×1.5）
#let title_fw    = 18.20pt   // 篇章標題 title（×1.3）
#let subtitle_fw = 14.00pt   // 副標題 subtitle（×1.0）
#let author_fw   = 11.20pt   // 著者 author（×0.8）
#let interp_fw   = 11.20pt   // 注疏 interp（×0.8）
#let note_fw     = 7.56pt   // 夾注 note（×0.54，≈½正文）
#let ns          = 7.56pt   // 同 note_fw（兼容旧写法）
#let pagenum_fw  = 9.80pt   // 頁碼 pagenum（×0.7）
#let cs_r        = 0.2000   // 字格行距比例（字高 × (1+cs_r) = 字格高）

// ── 核心竖排函数 vcol ────────────────────────────────
// 用法：#vcol("文字")          ← 正文字号
//       #vcol("文字", fw: title_fw)  ← 篇章標題
//       #vcol("文字", fw: note_fw)   ← 夾注
//       #vcol("文字", fw: heading_fw) ← 大標題
#let vcol(s, fw: cw) = {
  stack(dir: ttb,
    ..s.clusters().map(c =>
      box(width: fw, height: fw * (1 + cs_r))
        [#align(center + horizon)[#text(size: fw)[#c]]]
    )
  )
}

// ── 快捷样式函数（直接使用，无需记忆变量名）─────────
// 示例：#main("正文文字")  #title("標題")  #note("夾注") 
#let main(s)     = vcol(s, fw: cw)
#let heading(s)  = vcol(s, fw: heading_fw)
#let title(s)    = vcol(s, fw: title_fw)
#let subtitle(s) = vcol(s, fw: subtitle_fw)
#let author(s)   = vcol(s, fw: author_fw)
#let interp(s)   = vcol(s, fw: interp_fw)
#let note(s)     = vcol(s, fw: note_fw)

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