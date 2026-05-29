# GenBook - 古籍图片版 PDF 转可编辑 PDF 工具

## 项目目标

将不可编辑的图片版 PDF（竖版繁体古籍）转换为可编辑、可搜索的文字+图片混排 PDF。

核心需求：
- 仿原版竖排版式（从右到左，从上到下）
- 自定义字体、字号、行距、页边距等排版参数
- 图片区域原图裁剪，按原位坐标嵌入新 PDF
- 识别精准达到商业水准

---

## 设计决策

| 决策项 | 选择 |
|---|---|
| 输出排版 | 仿原版竖排，自定义字体重新排版 |
| 图片处理 | 原图裁剪，按原位坐标嵌入新 PDF |
| OCR 引擎 | Google Cloud Vision API（繁体中文，最高精度）|

---

## 系统架构

`
源PDF
  -> [1. PDF拆页  PyMuPDF 300DPI]
  -> [2. 版面分析 PPStructure（本地，只检测不OCR）]
  -> [3. 区域分类: 文字块 / 图片块]
       |-> [4a. Google Vision OCR 繁体竖排识别]
       |-> [4b. 原图裁剪，保存图片区域]
  -> [5. PageData 结构化中间数据]
  -> [6. ReportLab PDF重构引擎（竖排+自定义字体+图片嵌入）]
  -> 输出可编辑 PDF
`

---

## 项目目录结构

`
GenBook/
 main.py
 config/
    layout_config.yaml
 modules/
    pdf_reader.py
    layout_analyzer.py
    ocr_engine.py
    image_cropper.py
    page_model.py
    pdf_writer.py
 fonts/
 input/
 output/
 tests/
    conftest.py
    test_pdf_reader.py
    test_layout_analyzer.py
    test_ocr_engine.py
    test_image_cropper.py
    test_page_model.py
    test_pdf_writer.py
 requirements.txt
 prompt.md
`

---

## 技术栈

| 层 | 技术 | 用途 |
|---|---|---|
| PDF 解析 | PyMuPDF (fitz) | 拆页、高清图片提取 |
| 版面检测 | PaddleOCR PPStructure | 区域分类（本地）|
| OCR | Google Cloud Vision API | 繁体字符识别 |
| 图像处理 | Pillow, OpenCV | 预处理、裁剪 |
| 数据模型 | dataclasses | 结构化中间数据 |
| PDF 生成 | ReportLab | 竖排重构、字体嵌入 |
| 配置 | PyYAML | 排版参数外置 |
| 测试 | pytest | 单元测试 |
| 语言 | Python 3.11+ |  |

---

## 排版配置 layout_config.yaml 说明

- font_family: NotoSerifCJKtc
- font_path: fonts/NotoSerifCJKtc-Regular.ttf
- font_size: 14
- line_spacing: 1.8
- column_spacing: 10
- page_margin: top=36, bottom=36, left=36, right=36
- page_size: original  (A4 或 original)
- writing_mode: vertical-rl
- image_scale: 1.0
- ocr_confidence_threshold: 0.7

---

## 实现阶段规划

### 阶段 1 - 基础管道
- Task 1: pdf_reader.py  PDF 拆页，输出高清图片
- Task 2: layout_analyzer.py  版面分析，区分文字/图片区域

### 阶段 2 - 识别核心
- Task 3: ocr_engine.py  Google Vision OCR + 竖排字符排序
- Task 4: image_cropper.py  图片区域裁剪

### 阶段 3 - 数据与重构
- Task 5: page_model.py  结构化数据模型
- Task 6: pdf_writer.py  ReportLab 竖排绘制引擎

### 阶段 4 - 集成
- Task 7: main.py  主流程串联 + 端到端测试

---

## 关键技术难点

| 难点 | 解决方案 |
|---|---|
| 竖排字符顺序 | Google Vision 返回字符 bounding box，按 X 从右到左、Y 从上到下重排 |
| 图文坐标映射 | 记录原始 DPI 与页面尺寸，统一转换为 PDF 点坐标（1pt=1/72 inch）|
| 繁体识别率 | DOCUMENT_TEXT_DETECTION + languageHints zh-TW |
| 列检测精度 | PPStructure + 自定义后处理（合并碎片列、过滤噪点）|
| 字体嵌入 | ReportLab TTFont 注册 + 子集嵌入，确保 PDF 可搜索 |
