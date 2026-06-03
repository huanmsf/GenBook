# GenBook — 古籍 PDF OCR 转换工具

将**图片版 PDF**（扫描件、不可编辑）转换为**可搜索、可复制的文字 PDF**，专为竖排繁体古籍优化。

- 自动识别文字与图片区域
- 支持百度 / 腾讯 / Google 三大 OCR 云端引擎
- 保留竖排版式（从右到左），支持自定义字体
- 图片区域原位裁剪嵌入

---

## 目录

1. [环境要求](#1-环境要求)
2. [安装依赖](#2-安装依赖)
3. [配置 API 凭证（必填）](#3-配置-api-凭证必填)
4. [配置字体](#4-配置字体)
5. [运行转换](#5-运行转换)
6. [排版参数说明](#6-排版参数说明)
7. [版面元素样式系统](#7-版面元素样式系统)
8. [目录结构](#8-目录结构)
9. [注意事项](#9-注意事项)
10. [常用命令速查](#10-常用命令速查)

---

## 1. 环境要求

| 项目 | 要求 |
|---|---|
| Python | 3.10 或以上 |
| 操作系统 | Windows / macOS / Linux |
| 网络 | 需能访问所选 OCR 云服务（百度/腾讯/Google） |

---

## 2. 安装依赖

```bash
pip install -r requirements.txt
```

> **提示**：如遇 `paddlepaddle` 安装失败，可先单独安装 CPU 版本：
> ```bash
> pip install paddlepaddle -i https://pypi.tuna.tsinghua.edu.cn/simple
> ```

---

## 3. 配置 API 凭证（必填）

项目使用 `.env` 文件管理 API 凭证，**该文件不会提交到 git**。

### 第一步：复制模板文件

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

### 第二步：填写凭证

用任意文本编辑器打开 `.env`，按提示填入对应的 Key：

```ini
# 选择 OCR 后端：baidu | tencent | google（默认 baidu）
OCR_BACKEND=baidu

# ── 百度智能云 OCR ──────────────────────────────
# 申请地址：https://cloud.baidu.com/product/ocr_general
# 进入控制台 → 文字识别 → 创建应用 → 获取 AppID / API Key / Secret Key
BAIDU_OCR_APP_ID=填入你的AppID
BAIDU_OCR_API_KEY=填入你的APIKey
BAIDU_OCR_SECRET_KEY=填入你的SecretKey

# ── 腾讯云 OCR（如使用腾讯后端则填写）────────────
# 申请地址：https://cloud.tencent.com/product/ocr
# TENCENT_SECRET_ID=填入你的SecretId
# TENCENT_SECRET_KEY=填入你的SecretKey
# TENCENT_REGION=ap-guangzhou

# ── Google Cloud Vision（如使用 Google 后端则填写）─
# 申请地址：https://cloud.google.com/vision
# GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
```

> ⚠️ **注意**：`.env` 文件含私钥，请勿分享或提交到版本控制系统。

---

## 4. 配置字体

工具使用 TrueType / TrueType Collection 字体渲染汉字。**字体文件须手动准备**。

### 方法 A：使用系统字体（推荐 Windows 用户）

```bash
# Windows 系统楷体（繁体古籍效果佳）
copy C:\Windows\Fonts\STKAITI.TTF fonts\STKAITI.TTF

# 或宋体
copy C:\Windows\Fonts\simsun.ttc fonts\simsun.ttc
```

然后在 `config/layout_config.yaml` 中修改：

```yaml
font_family: "STKaiTi"
font_path:   "fonts/STKAITI.TTF"
```

### 方法 B：使用开源字体（跨平台）

下载 [Noto Serif CJK TC](https://fonts.google.com/noto/specimen/Noto+Serif+TC) 后：

```bash
# 将 .otf / .ttf 放入 fonts/ 目录
fonts/NotoSerifCJKtc-Regular.ttf
```

```yaml
font_family: "NotoSerifCJKtc"
font_path:   "fonts/NotoSerifCJKtc-Regular.ttf"
```

> ⚠️ **注意**：若 `font_path` 指向的文件不存在，输出 PDF 中的汉字将显示为黑色方块。

---

## 5. 运行转换

每次运行会在 `output/` 目录同时生成三个文件：

| 文件 | 说明 |
|---|---|
| `书名_out_时间戳.pdf` | 最终输出 PDF（由 Typst 编译） |
| `书名_out_时间戳.typ` | Typst 排版源文件（可用 Tinymist 预览/微调） |
| `书名_out_时间戳.ocr.json` | OCR 识别缓存（可跳过重新 OCR 重新生成） |

---

### 模式 A：完整流程（OCR → typ → PDF）

```bash
# 最简用法：转换整个 PDF
python main.py input/古籍.pdf

# 只转换第 1~10 页
python main.py input/古籍.pdf --pages 1-10

# 指定输出文件名
python main.py input/古籍.pdf --output 第一章.pdf

# 完整参数
python main.py input/古籍.pdf --pages 3-20 --output 结果.pdf --dpi 300 --confidence 0.7
```

---

### 模式 B：从 OCR 缓存重新生成 typ + PDF（调整配置后重排）

OCR 耗时较长。修改 `config/layout_config.yaml` 后，无需重跑 OCR，直接用缓存文件重新排版：

```bash
python main.py --from-cache output/书名_out_xxx.ocr.json --output 结果.pdf
```

---

### 模式 C：从 OCR 缓存只生成 typ（不编译 PDF）

适合先在 Tinymist 中预览排版效果，确认无误后再编译 PDF：

```bash
python main.py --from-cache output/书名_out_xxx.ocr.json --typ-only
```

> 输出的 `.typ` 文件与缓存同名，也可用 `--output 文件名.typ` 指定路径。

---

### 模式 D：从 typ 文件编译 PDF

在 Tinymist 里手动调整好 `.typ` 排版后，编译为最终 PDF：

```bash
python main.py --pdf-from-typ output/书名_out_xxx.typ
# 或指定输出路径
python main.py --pdf-from-typ output/书名_out_xxx.typ --output 最终版.pdf
```

---

### 参数说明

| 参数 | 说明 |
|---|---|
| `input_pdf` | 源 PDF 路径（模式A必填，其余可省略） |
| `--pages` / `-p` | 页码范围，格式 `起始-结束`，如 `1-10`（默认全部） |
| `--output` / `-o` | 输出文件名，自动存入 `output/`（默认：源名\_out\_时间戳） |
| `--dpi` | 渲染分辨率（默认 `300`，越高越清晰但越慢） |
| `--confidence` | OCR 置信度阈值（默认 `0.7`，低于此值的文字丢弃） |
| `--config` | 排版配置文件路径（默认 `config/layout_config.yaml`） |
| `--from-cache` | 指定 `.ocr.json` 缓存，跳过 OCR（模式B/C） |
| `--typ-only` | 与 `--from-cache` 配合，只生成 `.typ` 不编译 PDF（模式C） |
| `--pdf-from-typ` | 指定 `.typ` 文件直接编译 PDF（模式D） |

---

## 6. 排版参数说明

编辑 `config/layout_config.yaml` 可自定义输出效果：

```yaml
font_family: "STKaiTi"          # ReportLab 字体注册名
font_path:   "fonts/STKAITI.TTF" # 字体文件路径（相对项目根目录）
font_size:   14                  # 字号（磅）
line_spacing: 1.8                # 行距倍数
column_spacing: 10               # 列间距（磅）

page_margin:
  top:    36                     # 上边距（磅，1pt ≈ 0.35mm）
  bottom: 36
  left:   36
  right:  36

page_size:   "original"          # "original"（同源页尺寸）或 "A4"
writing_mode: "vertical-rl"      # 竖排从右到左（固定）
image_scale:  1.0                # 图片缩放比例
ocr_confidence_threshold: 0.7   # OCR 置信度阈值（同 --confidence）
```

---

## 7. 版面元素样式系统

GenBook 在生成的 `.typ` 文件中内建了一套**完整的竖排样式函数库**，覆盖港台出版常见排版元素。

---

### 7.1 样式元素一览

| 函数 | 变量 | 用途 | 默认字号（×14pt）|
|---|---|---|---|
| `#vmain("…")` | `cw` | 正文主体 | **14pt**（基准） |
| `#vheading("…")` | `heading_fw` | 大標題（卷名、書名大字） | **21pt**（×1.5）|
| `#vtitle("…")` | `title_fw` | 篇章標題（章節名） | **18.2pt**（×1.3）|
| `#vsubtitle("…")` | `subtitle_fw` | 副標題（標題下說明） | **14pt**（×1.0）|
| `#vauthor("…")` | `author_fw` | 著者 / 撰者 / 注者 | **11.2pt**（×0.8）|
| `#vinterp("…")` | `interp_fw` | 注疏 / 疏文（隨文解說） | **11.2pt**（×0.8）|
| `#vnote("…")` | `note_fw` | 夾注（雙行小字，≈½正文） | **7.6pt**（×0.54）|

所有字号从 `config/layout_config.yaml` 的 `styles` 节读取，**修改配置后重新生成即自动更新**。

---

### 7.2 在 `.typ` 文件中使用

生成的每一列默认是 `#vcol("文字", fw: cw)`（正文）。把它替换为对应的快捷函数或带 `fw:` 参数的写法即可：

#### 方法 A：快捷函数（推荐，语义清晰）

```typst
// 原始生成（正文）
#place(top + left, dx: 379.5pt, dy: 0.0pt,
  box(width: cw, height: 50.4pt)[#vcol("周易玩辭", fw: cw)])

// 改为篇章標題
#place(top + left, dx: 379.5pt, dy: 0.0pt,
  box(width: title_fw, height: 70.9pt)[#vtitle("周易玩辭")])
//   ↑ width 改用对应 fw 变量  ↑ height 重算：字数(4) × title_fw × (1+cs_r)
//                                          = 4 × 18.2 × 1.20 = 87.4pt

// 改为大標題
#place(top + left, dx: 379.5pt, dy: 0.0pt,
  box(width: heading_fw, height: 105.0pt)[#vheading("周易玩辭")])

// 改為夾注（雙行小字）
#place(top + left, dx: 245.9pt, dy: 0.0pt,
  box(width: note_fw, height: 18.2pt)[#vnote("玩辭")])
//                      ↑ height = 2 × 7.56 × 1.20 = 18.1pt
```

#### 方法 B：直接指定 fw 参数

```typst
// 著者行（author 字号）
box(width: author_fw, height: 80.6pt)[#vcol("江陵項安世述", fw: author_fw)]

// 注疏（interp 字号）
box(width: interp_fw, height: 134.4pt)[#vcol("程子曰此卦…", fw: interp_fw)]
```

---

### 7.3 高度计算公式

```
height = 字数 × fw × (1 + cs_r)
```

`cs_r` 定义在文件头（默认 0.2000）。常用速查：

| 字数 | `cw`(14pt) | `title_fw`(18.2pt) | `heading_fw`(21pt) | `note_fw`(7.56pt) |
|---|---|---|---|---|
| 1 | 16.8pt | 21.8pt | 25.2pt | 9.1pt |
| 2 | 33.6pt | 43.7pt | 50.4pt | 18.1pt |
| 4 | 67.2pt | 87.4pt | 100.8pt | 36.3pt |
| 6 | 100.8pt | 131.0pt | 151.2pt | 54.4pt |
| 8 | 134.4pt | 174.7pt | 201.6pt | 72.6pt |
| 20 | 336.0pt | — | — | — |

---

### 7.4 修改样式字号（通过配置）

编辑 `config/layout_config.yaml` 的 `styles` 节，修改倍率后重新生成：

```yaml
guji_layout:
  styles:
    main_scale:      1.00   # 正文基准（不建议改）
    heading_scale:   1.50   # 大標題 = font_size × 1.50
    title_scale:     1.30   # 篇章標題 = font_size × 1.30
    subtitle_scale:  1.00   # 副標題 = font_size × 1.00（同正文）
    author_scale:    0.80   # 著者 = font_size × 0.80
    interp_scale:    0.80   # 注疏 = font_size × 0.80
    note_scale:      0.54   # 夾注 = font_size × 0.54（≈½正文）
    pagenum_scale:   0.70   # 頁碼 = font_size × 0.70
```

例如将大標題改为正文的 1.8 倍：

```yaml
    heading_scale:   1.80   # → 14 × 1.80 = 25.2pt
```

重新生成后，`.typ` 文件头部的 `#let heading_fw` 会自动更新为 `25.20pt`。

---

### 7.5 直接在 `.typ` 文件顶部修改变量值

如果不想重跑生成，也可以直接修改 `.typ` 文件头部的 `#let` 声明，立即生效（Tinymist 热更新）：

```typst
// 修改前
#let title_fw    = 18.20pt   // 篇章標題 title（×1.3）

// 修改后（改为 20pt）
#let title_fw    = 20.00pt   // 篇章標題 title（×1.3）
```

所有使用 `fw: title_fw` 的列会立即以新字号渲染。

---

### 7.6 生成文件中的注释说明

每一列的注释已标明列号、字数、坐标：

```typst
// 列 2: main   字数=  8  cx=1774px  x_left=397.9pt  dy=0.0pt
#place(top + left, dx: 397.9pt, dy: 0.0pt,
  box(width: cw, height: 134.4pt)[#vcol("周易玩辭叙平圖書", fw: cw)])
```

手工调整时，**只需修改两处**：
1. `box(width: XX)` → 改为目标元素的 `fw` 变量名
2. `height` → 用公式重算（或直接用上方速查表）
3. `#vcol("…", fw: XX)` → 改为目标 `fw` 变量，或直接用快捷函数

---

## 8. 目录结构

```
GenBook/
├── main.py                  # 主入口（含四种运行模式）
├── requirements.txt         # Python 依赖
├── .env.example             # API 凭证模板（复制为 .env 后填写）
├── .env                     # 本地凭证文件（不提交 git）
│
├── config/
│   └── layout_config.yaml   # 排版配置（字号、边距、页码样式等）
│
├── fonts/                   # 字体文件目录（手动放入，不提交 git）
│   └── STKAITI.TTF
│
├── input/                   # 放置待转换的源 PDF
├── output/                  # 转换结果输出目录
│   ├── 书名_out_时间戳.pdf       # 最终 PDF（Typst 编译）
│   ├── 书名_out_时间戳.typ       # Typst 排版源文件
│   └── 书名_out_时间戳.ocr.json  # OCR 缓存（可重复利用）
│
└── modules/                 # 核心模块
    ├── pdf_reader.py        # PDF → 高清图片
    ├── layout_analyzer.py   # 版面分析（文字/图片区域检测）
    ├── ocr_engine.py        # OCR 识别（PaddleOCR）
    ├── ocr_cache.py         # OCR 结果缓存（序列化/反序列化）
    ├── image_cropper.py     # 图片区域裁剪
    ├── page_model.py        # 中间数据模型
    ├── typst_writer.py      # Typst 竖排源文件生成
    └── pdf_writer.py        # ReportLab PDF（降级备用）
```

---

## 9. 注意事项

| # | 注意事项 |
|---|---|
| 1 | **必须先创建 `.env` 文件**，否则运行时报 `KeyError`。方法见[第 3 节](#3-配置-api-凭证必填) |
| 2 | **字体文件需手动准备**，`fonts/` 目录不含字体，方法见[第 4 节](#4-配置字体) |
| 3 | `.env` 含私钥，**不要提交到 git、不要分享** |
| 4 | 百度 OCR 免费额度为每天 500 次，超出需付费；大量转换建议申请正式版 |
| 5 | 版面分析优先使用 `PPStructureV3`；若未安装完整 `paddlex` 依赖，自动降级为**整页识别模式**（适合满版文字的古籍） |
| 6 | 源 PDF 分辨率越高，OCR 效果越好；建议扫描件不低于 300 DPI |
| 7 | 输出文件（`.pdf` / `.typ` / `.ocr.json`）均保存在 `output/` 目录，**该目录不提交 git**，请自行备份 |
| 8 | `.typ` 文件可用 [Tinymist](https://marketplace.visualstudio.com/items?itemName=myriad-dreamin.tinymist) 插件实时预览，调整版式后用**模式D**重新编译 PDF |

---

## 快速开始（三步走）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 准备字体
copy C:\Windows\Fonts\STKAITI.TTF fonts\STKAITI.TTF

# 3. 运行转换（自动生成 PDF + typ + ocr.json）
python main.py input/你的古籍.pdf --pages 1-10
```

调整排版后**无需重跑 OCR**，直接从缓存重新生成：

```bash
# 修改 config/layout_config.yaml 后重排
python main.py --from-cache output/你的古籍_out_xxx.ocr.json

# 在 Tinymist 中微调 .typ 后编译 PDF
python main.py --pdf-from-typ output/你的古籍_out_xxx.typ
```

---

## 10. 常用命令速查

### 四种运行模式

| 模式 | 命令 | 说明 |
|---|---|---|
| A | `python main.py input/古籍.pdf --pages 1-20` | 完整流程：OCR → typ → PDF |
| B | `python main.py --from-cache output/xxx.ocr.json` | 从缓存重新生成 typ + PDF |
| C | `python main.py --from-cache output/xxx.ocr.json --typ-only` | 只生成 typ，不编译 PDF |
| D | `python main.py --pdf-from-typ output/xxx.typ` | 从 typ 编译 PDF |

### 典型工作流程

```
第一次运行（模式A）
  python main.py input/古籍.pdf --pages 1-50
  → 生成 output/古籍_out_xxx.pdf / .typ / .ocr.json

调整排版配置后（模式B，秒级）
  # 编辑 config/layout_config.yaml（字号、边距等）
  python main.py --from-cache output/古籍_out_xxx.ocr.json --output 古籍_v2.pdf

在 Tinymist 中微调后（模式D，秒级）
  # 用 VS Code + Tinymist 插件打开 .typ，手动调整个别列
  python main.py --pdf-from-typ output/古籍_out_xxx.typ --output 古籍_final.pdf
```

### 页码样式

在 `config/layout_config.yaml` 中修改：

```yaml
guji_layout:
  page_num_style: "arabic"   # 阿拉伯数字：1, 2, 100
  # page_num_style: "chinese" # 汉字：一、二、一百
```
