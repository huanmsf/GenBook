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
7. [目录结构](#7-目录结构)
8. [注意事项](#8-注意事项)

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

输出文件默认保存在 `output/` 目录。

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

## 7. 目录结构

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
```

---

## 8. 注意事项

| # | 注意事项 |
|---|---|
| 1 | **必须先创建 `.env` 文件**，否则运行时报 `KeyError`。方法见[第 3 节](#3-配置-api-凭证必填) |
| 2 | **字体文件需手动准备**，`fonts/` 目录不含字体，方法见[第 4 节](#4-配置字体) |
| 3 | `.env` 含私钥，**不要提交到 git、不要分享** |
| 4 | 百度 OCR 免费额度为每天 500 次，超出需付费；大量转换建议申请正式版 |
| 5 | 版面分析优先使用 `PPStructureV3`；若未安装完整 `paddlex` 依赖，自动降级为**整页识别模式**（适合满版文字的古籍） |
| 6 | 源 PDF 分辨率越高，OCR 效果越好；建议扫描件不低于 300 DPI |
| 7 | 输出 PDF 默认保存在 `output/` 目录，**该目录不提交 git**，请自行备份重要文件 |

---

## 快速开始（三步走）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 创建并填写凭证文件
copy .env.example .env
# → 用编辑器打开 .env，填入 BAIDU_OCR_APP_ID / API_KEY / SECRET_KEY

# 3. 准备字体并运行
copy C:\Windows\Fonts\STKAITI.TTF fonts\STKAITI.TTF
python main.py input/你的古籍.pdf --pages 1-10
```

