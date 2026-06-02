"""Patch README.md: update TOC and insert new section 7 about col type tuning."""
import pathlib, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

rp = pathlib.Path('README.md')
s  = rp.read_text(encoding='utf-8')

# ── 1. 更新目录 ────────────────────────────────────────────────────────
old_toc = (
    '7. [目录结构](#7-目录结构)\n'
    '8. [注意事项](#8-注意事项)\n'
)
new_toc = (
    '7. [正文 / 注文 / 标题调整指南](#7-正文--注文--标题调整指南)\n'
    '8. [目录结构](#8-目录结构)\n'
    '9. [注意事项](#9-注意事项)\n'
)
if old_toc in s:
    s = s.replace(old_toc, new_toc, 1)
    print('  OK: TOC updated')
else:
    print('  MISS: TOC not found')

# ── 2. 更新旧章节编号 7→8, 8→9 ───────────────────────────────────────
s = s.replace('## 7. 目录结构', '## 8. 目录结构')
s = s.replace('## 8. 注意事项', '## 9. 注意事项')
print('  OK: old section numbers updated')

# ── 3. 插入新第7节（在"## 7. 目录结构"原位前）────────────────────────
anchor = '## 8. 目录结构\n'
new_section = r"""## 7. 正文 / 注文 / 标题调整指南

生成的 `.typ` 文件中每一列都被自动标注了类型（`main` / `note` / `title`），不同类型会
用不同字号渲染：

| 类型 | 含义 | Typst 变量 | 默认字号 |
|---|---|---|---|
| `main` | 正文列 | `fw: cw`（`cw = font_size`） | 14pt（同正文） |
| `note` | 注文列（双行小字） | `fw: ns`（`ns = note_font_size`） | 7.5pt（正文½） |
| `title` | 标题 / 卷次列 | `fw: cw` | 14pt（同正文） |

---

### 7.1 自动分类逻辑

程序通过以下规则自动判断：

1. **注文列（`note`）**：与左右两侧邻列的 OCR cx 间距都 < 全页中位数间距 × `note_gap_ratio`（默认 0.55）  
   → 注文夹在两正文列之间，间距明显偏窄
2. **标题列（`title`）**：字数 ≤ `title_max_chars`（默认 12）
3. **正文列（`main`）**：其余所有列

> ⚠️ **自动分类并不总是准确**，尤其是：
> - 书名页、序页等非常规版式
> - 标题列与正文列相邻时被误判为注文
> - 注文列字数超过 12 字时被判为正文

---

### 7.2 在 `.typ` 文件中手工修正

生成的每一列注释都标明了类型，如：

```typst
// 列 2: note   字数=  8  cx=1774px  x_left=367.0pt  dy=0.0pt
#place(top + left, dx: 367.0pt, dy: 0.0pt, box(width: ns, height: 96.0pt)[#vcol("周易玩辭叙平圖書", fw: ns)])
```

**将 `note` 列改为 `title`（标题）**：把 `fw: ns` 和 `width: ns` 改为 `fw: cw` 和 `width: cw`，
并更新 `height`：

```typst
// 修改前（误判为注文，小字显示）
#place(top + left, dx: 367.0pt, dy: 0.0pt,
  box(width: ns, height: 96.0pt)[#vcol("周易玩辭叙平圖書", fw: ns)])

// 修改后（改为标题，正文字号显示）
#place(top + left, dx: 367.0pt, dy: 0.0pt,
  box(width: cw, height: 134.4pt)[#vcol("周易玩辭叙平圖書", fw: cw)])
//   ↑ width 改 cw       ↑ height = 字数(8) × cw × 1.2 = 8 × 14 × 1.2 = 134.4
```

**将 `main` 列改为 `note`（双行小字注释）**：把 `fw: cw` 改为 `fw: ns`，同时更新宽高：

```typst
// 修改前（正文大字）
#place(top + left, dx: 215.0pt, dy: 0.0pt,
  box(width: cw, height: 33.6pt)[#vcol("玩辭", fw: cw)])

// 修改后（注文小字）
#place(top + left, dx: 215.0pt, dy: 0.0pt,
  box(width: ns, height: 18.0pt)[#vcol("玩辭", fw: ns)])
//   ↑ width 改 ns       ↑ height = 字数(2) × ns × 1.2 = 2 × 7.5 × 1.2 = 18.0
```

**高度计算公式**：

```
height = 字数 × fw × (1 + cs_r)
```

其中 `cs_r = 0.20`（20% 行距比例，文件头部定义）。

| 情况 | fw | cs_r | 字数=2 | 字数=8 |
|---|---|---|---|---|
| 正文 / 标题 | `cw = 14pt` | 0.20 | `2×14×1.2 = 33.6pt` | `8×14×1.2 = 134.4pt` |
| 注文 | `ns = 7.5pt` | 0.20 | `2×7.5×1.2 = 18.0pt` | `8×7.5×1.2 = 72.0pt` |

---

### 7.3 通过配置调整分类阈值

在 `config/layout_config.yaml` 的 `guji_layout` 节中修改：

```yaml
guji_layout:
  # 列类型判断阈值
  note_gap_ratio:  0.55  # 提高此值（如 0.70）可让更多窄间距列被判为注文
                         # 降低此值（如 0.40）则更保守，减少误判
  title_max_chars: 12    # 字数≤此值且非注文列 → 标题
                         # 增大可让更多长标题被识别为 title 而非 main
```

**调整建议**：

| 问题现象 | 调整方向 |
|---|---|
| 标题列被判为正文（字号偏小）| 增大 `title_max_chars`（如改为 16）|
| 注文列被判为正文（小字变大）| 降低 `note_gap_ratio`（如改为 0.45）|
| 正文列被判为注文（大字变小）| 提高 `note_gap_ratio`（如改为 0.65），或手工修改 `.typ` |
| 整页都是正文（无标题/注文）| 正常现象，该页版式统一，无需调整 |

---

### 7.4 在 `.typ` 中直接修改字号

Typst 的 `#text(size: Xpt)` 可覆盖单列字号，无需修改 `fw` 变量：

```typst
// 某列希望用特定字号（如 18pt 大标题）
#place(top + left, dx: 379.5pt, dy: 185.5pt,
  box(width: 18pt, height: 64.8pt)[
    #vcol("國立正", fw: 18pt)
  //                ↑ 直接传入具体 pt 值
  ])
```

---

### 7.5 关于 `cw` 和 `ns` 变量

`.typ` 文件开头定义了两个全局变量：

```typst
#let cw = 14.0pt   // 正文字号（= config.font_size）
#let ns = 7.5pt    // 注文字号（= config.note_font_size）
#let cs_r = 0.2000 // 行距比例（0.20 = 字号的 20%）
```

- 修改 `config/layout_config.yaml` 的 `font_size` 和 `note_font_size` 后重新生成，`cw` / `ns` 会自动更新。
- 也可以直接在 `.typ` 文件里修改这两行，立即生效（不需重新运行 OCR）。

---

"""
if anchor in s:
    s = s.replace(anchor, new_section + anchor, 1)
    print('  OK: new section 7 inserted')
else:
    print(f'  MISS: anchor "{anchor[:30]}" not found')

rp.write_text(s, encoding='utf-8', newline='\r\n')
print('Done — README.md updated')
