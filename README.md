# GenBook — 古籍 PDF OCR 转换工具

将**图片版 PDF**（扫描件、不可编辑）转换为**可搜索、可复制的文字 PDF**，专为竖排繁体古籍优化。

- 自动识别文字与图片区域，支持百度 / 腾讯 / Google 三大 OCR 云端引擎
- 保留竖排版式（从右到左），输出 Typst 排版源文件（可在 Tinymist 中实时预览微调）
- 支持**流式 grid 模式**（默认，插删列方便）和**绝对坐标模式**两种排版方式

---

## 目录

1. [环境要求与安装](#1-环境要求与安装)
2. [配置 API 凭证](#2-配置-api-凭证)
3. [配置字体](#3-配置字体)
4. [运行转换](#4-运行转换)
5. [排版配置](#5-排版配置)
6. [目录结构](#6-目录结构)

---

## 1. 环境要求与安装

| 项目 | 要求 |
|---|---|
| Python | 3.10 或以上 |
| 操作系统 | Windows / macOS / Linux |
| 网络 | 需能访问所选 OCR 云服务 |

```bash
pip install -r requirements.txt
```

---

## 2. 配置 API 凭证

```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

用文本编辑器打开 `.env`，填入对应 Key（默认使用百度 OCR）：

```ini
OCR_BACKEND=baidu

BAIDU_OCR_APP_ID=填入你的AppID
BAIDU_OCR_API_KEY=填入你的APIKey
BAIDU_OCR_SECRET_KEY=填入你的SecretKey
```

> ⚠️ `.env` 含私钥，请勿提交到 git 或分享。

---

## 3. 配置字体

将字体文件放入 `fonts/` 目录，并在 `config/layout_config.yaml` 中指定：

```bash
# Windows 系统楷体
copy C:\Windows\Fonts\STKAITI.TTF fonts\STKAITI.TTF
```

```yaml
font_family: "STKaiTi"
font_path:   "fonts/STKAITI.TTF"
```

跨平台可用 [Noto Serif CJK TC](https://fonts.google.com/noto/specimen/Noto+Serif+TC)，下载后放入 `fonts/` 并更新配置。

---

## 4. 运行转换

每次运行在 `output/` 同时生成三个文件：

| 文件 | 说明 |
|---|---|
| `书名_out_时间戳.pdf` | 最终 PDF（Typst 编译） |
| `书名_out_时间戳.typ` | Typst 排版源文件（可用 Tinymist 预览/微调） |
| `书名_out_时间戳.ocr.json` | OCR 缓存（可跳过 OCR 重新排版） |

### 快速开始

```bash
# 完整流程：OCR → 流式 typ → PDF（默认）
python main.py input/古籍.pdf --pages 1-20

# 使用绝对坐标模式
python main.py input/古籍.pdf --pages 1-20 --no-flow
```

### 四种运行模式

| 模式 | 命令 |
|---|---|
| A 完整流程 | `python main.py input/古籍.pdf --pages 1-20` |
| B 从缓存重新生成 typ + PDF | `python main.py --from-cache output/xxx.ocr.json` |
| C 从缓存只生成 typ | `python main.py --from-cache output/xxx.ocr.json --typ-only` |
| D 从 typ 编译 PDF | `python main.py --pdf-from-typ output/xxx.typ` |

### 排版模式切换

| 参数 | 说明 |
|---|---|
| `--flow`（默认） | 流式 grid 竖排：列顺序即显示顺序，插删列只需增删 grid 子项 |
| `--no-flow` | 绝对坐标竖排：每列用 `#place(dx,dy)` 精确定位 |

```bash
# 模式 B/C 同样支持 --no-flow
python main.py --from-cache output/xxx.ocr.json --typ-only --no-flow
```

### 典型工作流

```
1. 首次运行（模式 A）
   python main.py input/古籍.pdf --pages 1-50

2. 调整配置后重排（模式 B，秒级，无需重跑 OCR）
   python main.py --from-cache output/古籍_out_xxx.ocr.json --output 古籍_v2.pdf

3. 在 Tinymist 中微调 .typ 后编译（模式 D，秒级）
   python main.py --pdf-from-typ output/古籍_out_xxx.typ --output 古籍_final.pdf
```

### 完整参数

| 参数 | 说明 |
|---|---|
| `input_pdf` | 源 PDF 路径（模式 A 必填） |
| `--pages` / `-p` | 页码范围，如 `1-20`（默认全部） |
| `--output` / `-o` | 输出文件名（默认：源名\_out\_时间戳） |
| `--dpi` | 渲染分辨率（默认 `300`） |
| `--confidence` | OCR 置信度阈值（默认 `0.7`） |
| `--config` | 排版配置文件（默认 `config/layout_config.yaml`） |
| `--from-cache` | 指定 `.ocr.json` 跳过 OCR |
| `--typ-only` | 与 `--from-cache` 配合，只生成 `.typ` |
| `--pdf-from-typ` | 直接从 `.typ` 编译 PDF |
| `--flow` / `--no-flow` | 流式模式 / 绝对坐标模式 |

---

## 5. 排版配置

编辑 `config/layout_config.yaml`：

```yaml
font_family: "STKaiTi"
font_size:   14          # 字号（磅）
line_spacing: 0          # 行距（0=自动，字号×20%）
column_spacing: 4        # 列间距（磅）

guji_layout:
  paper: "jis-b5"        # 纸张规格
  tian_tou_mm:    25     # 天头（上边距 mm）
  di_jiao_mm:     20     # 地脚（下边距 mm）
  zhuang_ding_mm: 20     # 装订侧边距 mm
  shu_kou_mm:     15     # 书口侧边距 mm
  show_page_num:  true
  page_num_style: "chinese"   # chinese | arabic

  styles:
    heading_scale:  1.50   # 大標題 = font_size × 1.50
    title_scale:    1.30   # 篇章標題
    author_scale:   0.80   # 著者
    note_scale:     0.54   # 夾注
```

> 修改配置后用**模式 B** 从缓存重新生成，无需重跑 OCR。

生成的 `.typ` 文件头部有完整的 `#let` 变量声明，也可直接在文件中修改，Tinymist 热更新即时生效。

---

## 6. 目录结构

```
GenBook/
├── main.py                  # 主入口（--help 查看所有参数）
├── requirements.txt
├── .env.example             # API 凭证模板
│
├── config/
│   └── layout_config.yaml   # 排版配置
│
├── fonts/                   # 字体文件（手动放入，不提交 git）
├── input/                   # 待转换的源 PDF
├── output/                  # 转换结果（pdf / typ / ocr.json）
│
├── modules/
│   ├── pdf_reader.py        # PDF → 高清图片
│   ├── layout_analyzer.py   # 版面分析
│   ├── ocr_engine.py        # OCR 识别（PaddleOCR）
│   ├── ocr_cache.py         # OCR 缓存序列化
│   ├── image_cropper.py     # 图片区域裁剪
│   ├── page_model.py        # 中间数据模型
│   ├── typst_flow_writer.py # 流式 grid 竖排生成（默认）
│   ├── typst_writer.py      # 绝对坐标竖排生成（--no-flow）
│   └── pdf_writer.py        # ReportLab PDF（降级备用）
│
└── tests/
    ├── preview_flow_typ.py  # 将绝对坐标 .typ / .ocr.json 转流式 .typ
    └── test_*.py            # 单元测试
```
