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
import pathlib
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
    stem = os.path.splitext(os.path.basename(input_pdf or "output"))[0]
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
            "排版模式:\n"
            "  --flow      (默认) 流式 grid 竖排：列顺序即显示顺序，插删列只需增删 grid 子项\n"
            "  --no-flow   绝对坐标竖排：每列用 #place(dx,dy) 精确定位，移列须逐一改坐标\n"
            "\n"
            "示例:\n"
            "  # 完整流程：OCR → 流式 typ → PDF（默认流式模式）\n"
            "  python main.py input/古籍.pdf --pages 3-10\n"
            "\n"
            "  # 完整流程：使用绝对坐标模式\n"
            "  python main.py input/古籍.pdf --pages 3-10 --no-flow\n"
            "\n"
            "  # 从 OCR 缓存只生成流式 typ（不编译 PDF）\n"
            "  python main.py --from-cache output/xxx.ocr.json --typ-only\n"
            "\n"
            "  # 从 OCR 缓存只生成绝对坐标 typ\n"
            "  python main.py --from-cache output/xxx.ocr.json --typ-only --no-flow\n"
            "\n"
            "  # 从 OCR 缓存重新生成流式 typ + PDF\n"
            "  python main.py --from-cache output/xxx.ocr.json --output 结果.pdf\n"
            "\n"
            "  # 从 typ 文件编译 PDF\n"
            "  python main.py --pdf-from-typ output/xxx.typ\n"
        ),
    )
    parser.add_argument(
        "input_pdf",
        nargs="?",
        default=None,
        help="源 PDF 文件路径（使用 --from-cache 时可省略）",
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
    parser.add_argument(
        "--from-cache",
        dest="from_cache",
        default=None,
        metavar="FILE.ocr.json",
        help="跳过 OCR，直接从缓存文件重新生成 PDF 和 Typst 源文件",
    )
    parser.add_argument(
        "--typ-only",
        dest="typ_only",
        action="store_true",
        default=False,
        help="与 --from-cache 配合：只生成 .typ 源文件，不编译 PDF",
    )
    parser.add_argument(
        "--pdf-from-typ",
        dest="pdf_from_typ",
        default=None,
        metavar="FILE.typ",
        help="直接从 .typ 文件编译生成 PDF（无需 OCR）",
    )
    parser.add_argument(
        "--flow",
        dest="flow",
        action="store_true",
        default=True,
        help="使用流式 grid 竖排模式生成 .typ（默认开启）",
    )
    parser.add_argument(
        "--no-flow",
        dest="flow",
        action="store_false",
        help="使用绝对坐标竖排模式生成 .typ（回退到 typst_writer）",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# 主处理流程
# ---------------------------------------------------------------------------

def _compile_typ_to_pdf(typ_path: str, output_pdf: str) -> bool:
    """用 typst Python 包把 .typ 编译为 PDF。
    返回 True=成功，False=typst 不可用（调用方可降级到 ReportLab）。
    """
    try:
        import typst as _typst
        import pathlib as _pl
        # typst.compile() 返回 bytes
        pdf_bytes = _typst.compile(typ_path)
        _pl.Path(output_pdf).write_bytes(pdf_bytes)
        return True
    except ImportError:
        log.warning("typst 包未安装，降级使用 ReportLab 输出 PDF")
        return False
    except Exception as e:
        log.warning(f"typst 编译失败: {e}，降级使用 ReportLab")
        return False


def generate_typ_only(
    cache_path: str,
    typ_path: str | None = None,
    config_path: str = "config/layout_config.yaml",
    flow: bool = True,
) -> str:
    """从 .ocr.json 缓存只生成 .typ 文件，不编译 PDF。
    返回生成的 .typ 文件路径。
    flow=True（默认）流式 grid 竖排；flow=False 绝对坐标竖排。
    """
    from modules.ocr_cache import load_ocr_cache
    from modules.pdf_writer import load_config
    from modules.typst_flow_writer import create_typst
    from modules.typst_writer import build_typ_output_path

    log.info(f"读取 OCR 缓存: {cache_path}")
    all_pages = load_ocr_cache(cache_path)
    log.info(f"共 {len(all_pages)} 页")

    config = load_config(config_path)

    if typ_path is None:
        # 与缓存文件同名，替换扩展名
        typ_path = pathlib.Path(cache_path).with_suffix('').with_suffix('.typ').as_posix()
        # xxx.ocr.json → xxx.typ
        if typ_path.endswith('.ocr'):
            typ_path = typ_path[:-4] + '.typ'

    mode = "流式grid" if flow else "绝对坐标"
    log.info(f"生成 Typst 源文件（{mode}模式）: {typ_path}")
    create_typst(all_pages, typ_path, config, flow=flow)
    log.info(f"完成！Typst 文件: {os.path.abspath(typ_path)}")
    return typ_path


def compile_pdf_from_typ(typ_path: str, output_pdf: str | None = None) -> str:
    """从 .typ 文件编译生成 PDF。
    返回生成的 PDF 文件路径。
    """
    if output_pdf is None:
        stem = pathlib.Path(typ_path).stem   # e.g. zywc_out_20260603135931
        os.makedirs("output", exist_ok=True)
        output_pdf = os.path.join("output", stem + ".pdf")

    log.info(f"编译: {typ_path}  →  {output_pdf}")
    ok = _compile_typ_to_pdf(typ_path, output_pdf)
    if not ok:
        log.error("typst 编译失败，且无 ReportLab 降级路径（需要 OCR 数据才能降级）")
        raise RuntimeError(f"typst 编译失败: {typ_path}")
    log.info(f"完成！PDF 文件: {os.path.abspath(output_pdf)}")
    return output_pdf


def process(
    input_pdf: str,
    output_pdf: str,
    config_path: str = "config/layout_config.yaml",
    dpi: int = 300,
    confidence_threshold: float = 0.7,
    page_start: int | None = None,
    page_end: int | None = None,
    flow: bool = True,
) -> None:
    """主处理流程：读取 PDF → 版面分析 → OCR → 重构 PDF。
    flow=True（默认）流式 grid 竖排；flow=False 绝对坐标竖排。
    """
    from modules.pdf_reader import pdf_to_images
    from modules.layout_analyzer import analyze_layout, Region
    from modules.ocr_engine import recognize_region, sort_vertical_chars
    from modules.image_cropper import crop_image_region
    from modules.page_model import PageData, TextColumn, CharData, ImageRegion
    from modules.pdf_writer import load_config, create_pdf
    from modules.typst_flow_writer import create_typst as _flow_create
    from modules.typst_writer import create_typst as _abs_create, build_typ_output_path
    _create_typst = _flow_create if flow else _abs_create

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

    # 保存 OCR 缓存（.ocr.json），可用 --from-cache 重新生成
    from modules.ocr_cache import save_ocr_cache, cache_path_for
    cache_file = cache_path_for(output_pdf)
    save_ocr_cache(all_pages, cache_file)
    log.info(f"OCR 缓存已保存: {os.path.abspath(cache_file)}")

    # 生成 Typst 源文件
    typ_path = build_typ_output_path(output_pdf)
    mode = "流式grid" if flow else "绝对坐标"
    log.info(f"生成 Typst 源文件（{mode}模式）: {typ_path}")
    _create_typst(all_pages, typ_path, config, flow=flow)
    log.info(f"Typst 源文件: {os.path.abspath(typ_path)}")

    # 主路：typst.compile() → PDF（与 typ 样式一致）
    log.info(f"编译 PDF: {output_pdf}")
    ok = _compile_typ_to_pdf(typ_path, output_pdf)
    if not ok:
        # 降级：ReportLab（布局较简陋，仅供应急）
        log.warning("降级使用 ReportLab 生成 PDF（布局与 Typst 不同）")
        create_pdf(all_pages, output_pdf, config)
    log.info(f"完成！输出文件: {os.path.abspath(output_pdf)}")


# ---------------------------------------------------------------------------
# 从缓存重新生成（跳过 OCR）
# ---------------------------------------------------------------------------

def process_from_cache(
    cache_path: str,
    output_pdf: str,
    config_path: str = "config/layout_config.yaml",
    flow: bool = True,
) -> None:
    """从 .ocr.json 缓存直接生成 PDF 和 Typst 文件，无需重跑 OCR。
    flow=True（默认）流式 grid 竖排；flow=False 绝对坐标竖排。
    """
    from modules.ocr_cache import load_ocr_cache
    from modules.pdf_writer import load_config, create_pdf
    from modules.typst_flow_writer import create_typst as _flow_create
    from modules.typst_writer import create_typst as _abs_create, build_typ_output_path
    _create_typst = _flow_create if flow else _abs_create

    log.info(f"读取 OCR 缓存: {cache_path}")
    all_pages = load_ocr_cache(cache_path)
    log.info(f"共 {len(all_pages)} 页")

    config = load_config(config_path)

    # 生成 Typst 源文件
    typ_path = build_typ_output_path(output_pdf)
    mode = "流式grid" if flow else "绝对坐标"
    log.info(f"生成 Typst 源文件（{mode}模式）: {typ_path}")
    _create_typst(all_pages, typ_path, config, flow=flow)
    log.info(f"Typst 源文件: {os.path.abspath(typ_path)}")

    # 主路：typst.compile() → PDF
    log.info(f"编译 PDF: {output_pdf}")
    ok = _compile_typ_to_pdf(typ_path, output_pdf)
    if not ok:
        log.warning("降级使用 ReportLab 生成 PDF")
        create_pdf(all_pages, output_pdf, config)
    log.info(f"完成！输出文件: {os.path.abspath(output_pdf)}")


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
        if args.pdf_from_typ:
            # 模式 A：直接从 .typ 编译 PDF
            out_pdf = build_output_path(args.pdf_from_typ, args.output_pdf) if args.output_pdf else None
            compile_pdf_from_typ(
                typ_path=args.pdf_from_typ,
                output_pdf=out_pdf,
            )
        elif args.from_cache and args.typ_only:
            # 模式 B：从 OCR 缓存只生成 typ
            generate_typ_only(
                cache_path=args.from_cache,
                typ_path=args.output_pdf,   # 用 --output 指定 typ 路径（可选）
                config_path=args.config,
                flow=args.flow,
            )
        elif args.from_cache:
            # 模式 C：从 OCR 缓存生成 typ + PDF
            process_from_cache(
                cache_path=args.from_cache,
                output_pdf=output_pdf,
                config_path=args.config,
                flow=args.flow,
            )
        else:
            # 模式 D：完整流程 OCR → typ → PDF
            if not args.input_pdf:
                log.error("请提供源 PDF 路径，或使用 --from-cache / --pdf-from-typ")
                sys.exit(1)
            process(
                input_pdf=args.input_pdf,
                output_pdf=output_pdf,
                config_path=args.config,
                dpi=args.dpi,
                confidence_threshold=args.confidence,
                page_start=page_start,
                page_end=page_end,
                flow=args.flow,
            )
    except Exception as e:
        log.error(f"处理失败: {e}")
        sys.exit(1)

