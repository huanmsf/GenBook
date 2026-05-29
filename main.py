"""GenBook CLI — 古籍图片版 PDF 转可编辑竖排 PDF 主入口。

用法:
    # 最简用法（转换所有页，自动生成输出文件名）
    python main.py input/source.pdf

    # 指定输出文件名
    python main.py input/source.pdf --output result.pdf

    # 只转换第 3~10 页
    python main.py input/source.pdf --pages 3-10

    # 全参数
    python main.py input/source.pdf --output result.pdf --pages 5-20 --dpi 300
"""
from __future__ import annotations
import argparse
import logging
import os
import re
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def parse_pages(pages_str: str | None) -> tuple[int | None, int | None]:
    """解析 '起始页-终止页' 字符串，返回 (start, end)。

    Args:
        pages_str: 格式为 '3-10' 的字符串，或 None（表示全部页）。

    Returns:
        (page_start, page_end) 均为 1-based int，或 (None, None)。

    Raises:
        ValueError: 格式非法或 start > end。
    """
    if pages_str is None:
        return None, None

    match = re.fullmatch(r"(\d+)-(\d+)", pages_str.strip())
    if not match:
        raise ValueError(
            f"页码范围格式错误: '{pages_str}'，正确格式为 '起始页-终止页'，例如 '3-10'。"
        )
    start, end = int(match.group(1)), int(match.group(2))
    if start > end:
        raise ValueError(
            f"起始页 {start} 不能大于终止页 {end}。"
        )
    return start, end


def build_output_path(input_pdf: str, output_name: str | None = None) -> str:
    """构建输出 PDF 路径。

    Args:
        input_pdf:   源 PDF 路径（用于提取文件名）。
        output_name: 用户指定的输出文件名（可含路径），None 时自动生成。

    Returns:
        输出文件的完整路径字符串。
        - 指定名称时：output/<output_name>（如名称已含路径则直接使用）
        - 自动生成时：output/<源文件名>_out_<时间戳>.pdf
    """
    os.makedirs("output", exist_ok=True)

    if output_name:
        # 如果用户只给了文件名（无目录），放到 output/ 下
        if os.path.dirname(output_name) == "":
            return os.path.join("output", output_name)
        return output_name

    # 自动生成：源文件名 + _out_ + 时间戳
    stem = os.path.splitext(os.path.basename(input_pdf))[0]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return os.path.join("output", f"{stem}_out_{timestamp}.pdf")


# ---------------------------------------------------------------------------
# CLI 参数解析
# ---------------------------------------------------------------------------

def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GenBook: 将图片版 PDF 古籍转换为可编辑竖排 PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python main.py input/古籍.pdf\n"
            "  python main.py input/古籍.pdf --pages 3-10\n"
            "  python main.py input/古籍.pdf --output 结果.pdf --pages 1-50\n"
        ),
    )
    parser.add_argument(
        "input_pdf",
        help="源 PDF 文件路径（必填）",
    )
    parser.add_argument(
        "--output", "-o",
        dest="output_pdf",
        default=None,
        metavar="OUTPUT.pdf",
        help="输出 PDF 文件名（选填，默认: 源文件名_out_时间戳.pdf）",
    )
    parser.add_argument(
        "--pages", "-p",
        default=None,
        metavar="START-END",
        help="转换页码范围（选填，格式: 起始页-终止页，例如 3-10，默认转换所有页）",
    )
    parser.add_argument(
        "--config",
        default="config/layout_config.yaml",
        metavar="CONFIG",
        help="排版配置文件路径（默认: config/layout_config.yaml）",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="PDF 拆页分辨率（默认: 300，建议不低于 300）",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.7,
        help="OCR 置信度阈值，低于此值的字符将被过滤（默认: 0.7）",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# 主处理流程
# ---------------------------------------------------------------------------

def process(
    input_pdf: str,
    output_pdf: str,
    config_path: str = "config/layout_config.yaml",
    dpi: int = 300,
    confidence_threshold: float = 0.7,
    page_start: int | None = None,
    page_end: int | None = None,
) -> None:
    """主处理流程：读取 PDF → 版面分析 → OCR → 重构 PDF。"""
    from modules.pdf_reader import pdf_to_images
    from modules.layout_analyzer import analyze_layout, Region
    from modules.ocr_engine import recognize_region, sort_vertical_chars
    from modules.image_cropper import crop_image_region
    from modules.page_model import PageData, TextColumn, CharData, ImageRegion
    from modules.pdf_writer import load_config, create_pdf
    from modules.typst_writer import create_typst, build_typ_output_path

    config = load_config(config_path)

    page_range_desc = (
        f"第 {page_start}~{page_end} 页"
        if page_start or page_end
        else "全部页"
    )
    log.info(f"读取 PDF: {input_pdf}  [{page_range_desc}]")

    page_images = pdf_to_images(
        input_pdf, dpi=dpi,
        page_start=page_start,
        page_end=page_end,
    )
    log.info(f"共处理 {len(page_images)} 页")

    all_pages: list[PageData] = []

    for page_img in page_images:
        log.info(f"  处理第 {page_img.page_num} 页 ...")

        regions: list[Region] = analyze_layout(page_img.image_bytes)
        text_regions      = [r for r in regions if r.region_type == "text"]
        image_regions_meta = [r for r in regions if r.region_type == "image"]

        text_columns: list[TextColumn] = []
        for region in text_regions:
            raw_chars    = recognize_region(
                page_img.image_bytes,
                region_bbox=region.bbox,
                confidence_threshold=confidence_threshold,
            )
            sorted_chars = sort_vertical_chars(raw_chars)
            text_columns.append(TextColumn(
                bbox=region.bbox,
                chars=[CharData(text=c.text, bbox=c.bbox, confidence=c.confidence)
                       for c in sorted_chars],
            ))

        cropped_images: list[ImageRegion] = []
        for region in image_regions_meta:
            try:
                cropped = crop_image_region(
                    page_img.image_bytes, region.bbox, page_img.page_num
                )
                cropped_images.append(
                    ImageRegion(bbox=cropped.bbox, image_bytes=cropped.image_bytes)
                )
            except ValueError as e:
                log.warning(f"    跳过图片区域 {region.bbox}: {e}")

        all_pages.append(PageData(
            page_num=page_img.page_num,
            orig_width_px=page_img.orig_width_px,
            orig_height_px=page_img.orig_height_px,
            dpi=dpi,
            text_columns=text_columns,
            image_regions=cropped_images,
        ))

    log.info(f"生成 PDF: {output_pdf}")
    create_pdf(all_pages, output_pdf, config)
    log.info(f"完成！输出文件: {os.path.abspath(output_pdf)}")

    # 同步生成 Typst 源文件（与 PDF 同目录，扩展名 .typ）
    typ_path = build_typ_output_path(output_pdf)
    log.info(f"生成 Typst 源文件: {typ_path}")
    create_typst(all_pages, typ_path, config)
    log.info(f"完成！Typst 文件: {os.path.abspath(typ_path)}")
    log.info(f"  编译为 PDF: typst compile \"{os.path.abspath(typ_path)}\"")


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = parse_args()

    # 解析页码范围
    try:
        page_start, page_end = parse_pages(args.pages)
    except ValueError as e:
        log.error(str(e))
        sys.exit(1)

    # 构建输出路径
    output_pdf = build_output_path(args.input_pdf, args.output_pdf)

    log.info(f"输出路径: {output_pdf}")

    try:
        process(
            input_pdf=args.input_pdf,
            output_pdf=output_pdf,
            config_path=args.config,
            dpi=args.dpi,
            confidence_threshold=args.confidence,
            page_start=page_start,
            page_end=page_end,
        )
    except Exception as e:
        log.error(f"处理失败: {e}")
        sys.exit(1)

