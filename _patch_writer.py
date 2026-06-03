"""Patch README.md: update section 5, 8, add section 10."""
import pathlib, re

p = pathlib.Path('README.md')
src = p.read_text(encoding='utf-8')

# ── 1. 目录：加第10条 ──────────────────────────────────────────────────────────
src = src.replace(
    '9. [注意事项](#9-注意事项)',
    '9. [注意事项](#9-注意事项)\n10. [常用命令速查](#10-常用命令速查)'
)

# ── 2. 第5节：完全替换运行转换部分 ────────────────────────────────────────────
old_sec5 = '''\
## 5. 运行转换

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

### 参数说明

| 参数 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `input_pdf` | ✅ | — | 源 PDF 路径 |
| `--pages` / `-p` | ❌ | 全部页 | 页码范围，格式 `起始-结束`，如 `1-10` |
| `--output` / `-o` | ❌ | `源名_out_时间戳.pdf` | 输出文件名（自动存入 `output/`） |
| `--dpi` | ❌ | `300` | 页面渲染分辨率，越高越清晰但越慢 |
| `--confidence` | ❌ | `0.7` | OCR 置信度阈值，低于此值的文字丢弃 |
| `--config` | ❌ | `config/layout_config.yaml` | 自定义排版配置文件路径 |

输出文件默认保存在 `output/` 目录。'''

new_sec5 = '''\
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
| `--pdf-from-typ` | 指定 `.typ` 文件直接编译 PDF（模式D） |'''

src = src.replace(old_sec5, new_sec5)

# ── 3. 第8节目录结构：更新模块列表 ──────────────────────────────────────────
old_struct = '''\
```
GenBook/
├── main.py                  # 主入口
├── requirements.txt         # Python 依赖
├── .env.example             # API 凭证模板（复制为 .env 后填写）
├── .env                     # 本地凭证文件（不提交 git）
│
├── config/
│   └── layout_config.yaml   # 排版配置
│
├── fonts/                   # 字体文件目录（手动放入，不提交 git）
│   └── STKAITI.TTF
│
├── input/                   # 放置待转换的源 PDF
├── output/                  # 转换结果输出目录
│
└── modules/                 # 核心模块
    ├── pdf_reader.py        # PDF → 高清图片
    ├── layout_analyzer.py   # 版面分析（文字/图片区域检测）
    ├── ocr_engine.py        # OCR 识别（多后端）
    ├── image_cropper.py     # 图片区域裁剪
    ├── page_model.py        # 中间数据模型
    └── pdf_writer.py        # 竖排 PDF 重构
```'''

new_struct = '''\
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
```'''

src = src.replace(old_struct, new_struct)

# ── 4. 第9节注意事项：更新过时条目 ──────────────────────────────────────────
src = src.replace(
    '| 7 | 输出 PDF 默认保存在 `output/` 目录，**该目录不提交 git**，请自行备份重要文件 |',
    '| 7 | 输出文件（`.pdf` / `.typ` / `.ocr.json`）均保存在 `output/` 目录，**该目录不提交 git**，请自行备份 |\n| 8 | `.typ` 文件可用 [Tinymist](https://marketplace.visualstudio.com/items?itemName=myriad-dreamin.tinymist) 插件实时预览，调整版式后用**模式D**重新编译 PDF |'
)

# ── 5. 快速开始：更新为新流程 ─────────────────────────────────────────────────
old_quick = '''\
## 快速开始（三步走）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 创建并填写凭证文件
copy .env.example .env
# → 用编辑器打开 .env，填入 BAIDU_OCR_APP_ID / API_KEY / SECRET_KEY

# 3. 准备字体并运行
copy C:\\Windows\\Fonts\\STKAITI.TTF fonts\\STKAITI.TTF
python main.py input/你的古籍.pdf --pages 1-10
```'''

new_quick = '''\
## 快速开始（三步走）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 准备字体
copy C:\\Windows\\Fonts\\STKAITI.TTF fonts\\STKAITI.TTF

# 3. 运行转换（自动生成 PDF + typ + ocr.json）
python main.py input/你的古籍.pdf --pages 1-10
```

调整排版后**无需重跑 OCR**，直接从缓存重新生成：

```bash
# 修改 config/layout_config.yaml 后重排
python main.py --from-cache output/你的古籍_out_xxx.ocr.json

# 在 Tinymist 中微调 .typ 后编译 PDF
python main.py --pdf-from-typ output/你的古籍_out_xxx.typ
```'''

src = src.replace(old_quick, new_quick)

# ── 6. 新增第10节常用命令速查 ─────────────────────────────────────────────────
sec10 = '''
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
'''

# 追加到文件末尾（在最后的换行前）
src = src.rstrip() + '\n' + sec10

p.write_text(src, encoding='utf-8', newline='\r\n')
print('OK: README.md updated')

# verify
checks = [
    ('section 10 added',      '## 10. 常用命令速查' in src),
    ('mode A in sec5',        '模式 A：完整流程' in src),
    ('mode B in sec5',        '模式 B：从 OCR 缓存重新生成' in src),
    ('mode C in sec5',        '模式 C：从 OCR 缓存只生成 typ' in src),
    ('mode D in sec5',        '模式 D：从 typ 文件编译 PDF' in src),
    ('--from-cache param row', '`--from-cache`' in src),
    ('--typ-only param row',   '`--typ-only`' in src),
    ('--pdf-from-typ param row','`--pdf-from-typ`' in src),
    ('ocr_cache.py in struct', 'ocr_cache.py' in src),
    ('typst_writer.py in struct','typst_writer.py' in src),
]
for name, ok in checks:
    print(f'  [{"OK" if ok else "FAIL"}] {name}')
