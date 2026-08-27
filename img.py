"""GenBook CLI — 图片文件转可编辑 PDF（竖排 / 横排）。

与 main.py 平行的入口：输入是图片（单文件、多文件或目录），而不是 PDF。
OCR / 版面分析 / 缓存 / Typst 编译均复用现有模块；横排走新的
typst_horizontal_writer，不修改 typst_flow_writer / main.py 的原有方法。

横排默认 --no-flow（文字 #place 到原图对应位置）；竖排默认 --flow。

用法:
    python img.py input/page.png
    python img.py input/scans/ --pages 1-15
    python img.py a.png b.png --layout horizontal --config config/layout_config_modern_cn.yaml
    python img.py --from-cache output/xxx.ocr.json --layout vertical
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(override=False)
except ImportError:
    pass

from main import (
    parse_pages,
    build_output_path,
    _compile_typ_to_pdf,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def _is_horizontal_config(config: dict) -> bool:
    mode = str(config.get("writing_mode", "vertical-rl")).lower().replace("_", "-")
    return mode in ("horizontal-tb", "horizontal", "horizontal-lr", "ltr")


def resolve_layout(layout_arg: str, config: dict) -> str:
    """返回 'horizontal' 或 'vertical'。"""
    if layout_arg == "auto":
        return "horizontal" if _is_horizontal_config(config) else "vertical"
    return layout_arg


def resolve_flow(flow_arg, layout: str) -> bool:
    """横排默认绝对坐标（no-flow）；竖排默认流式。显式 --flow / --no-flow 优先。"""
    if flow_arg is not None:
        return bool(flow_arg)
    return layout != "horizontal"


def _pick_typst_writer(layout: str, flow: bool):
    if layout == "horizontal":
        from modules.typst_horizontal_writer import create_typst as _h

        def _wrapped(pages, path, config):
            return _h(pages, path, config, flow=flow)

        return _wrapped
    if flow:
        from modules.typst_flow_writer import create_typst as _flow

        def _wrapped(pages, path, config):
            return _flow(pages, path, config, flow=True)

        return _wrapped
    from modules.typst_writer import create_typst as _abs
    return _abs


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GenBook: 将古籍扫描图片转换为可编辑竖排或横排 PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python img.py input/page.png\n"
            "  python img.py input/scans/ --pages 1-15 --config config/layout_config_modern_tw.yaml\n"
            "  python img.py page.png --layout horizontal --config config/layout_config_modern_cn.yaml\n"
            "  python img.py --from-cache output/xxx.ocr.json --layout horizontal --flow\n"
        ),
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        default=[],
        help="图片文件或目录（可多个；目录内按文件名排序）",
    )
    parser.add_argument("--output", "-o", dest="output_pdf", default=None)
    parser.add_argument("--pages", "-p", default=None, metavar="START-END")
    parser.add_argument(
        "--config",
        default=os.environ.get("LAYOUT_CONFIG", "config/layout_config.yaml"),
    )
    parser.add_argument("--dpi", type=int, default=300,
                        help="用于 px→pt 换算的假定 DPI（图片不再缩放，默认 300）")
    parser.add_argument("--confidence", type=float, default=0.7)
    parser.add_argument("--from-cache", dest="from_cache", default=None)
    parser.add_argument("--typ-only", dest="typ_only", action="store_true")
    parser.add_argument("--pdf-from-typ", dest="pdf_from_typ", default=None)
    parser.add_argument(
        "--layout",
        choices=("auto", "vertical", "horizontal"),
        default="auto",
        help="排版方向：auto=读配置 writing_mode；vertical=竖排；horizontal=横排",
    )
    parser.add_argument(
        "--flow", dest="flow", action="store_true", default=None,
        help="流式排版：竖排默认；横排需显式指定才会段落重排",
    )
    parser.add_argument(
        "--no-flow", dest="flow", action="store_false",
        help="绝对坐标：横排默认；竖排时每列 #place(dx,dy)",
    )
    return parser.parse_args(argv)


def ocr_pages_from_images(
    page_images,
    confidence_threshold: float,
    dpi: int,
):
    """图片 → 版面分析 → OCR → PageData。调用现有 analyze_layout 等，不改其实现。"""
    from modules.layout_analyzer import analyze_layout
    from modules.ocr_engine import sort_vertical_chars
    from modules.ocr_jpeg import recognize_region_safe
    from modules.image_cropper import crop_image_region
    from modules.page_model import PageData, TextColumn, CharData, ImageRegion

    all_pages: list[PageData] = []
    for page_img in page_images:
        log.info(f"  处理第 {page_img.page_num} 页 ...")
        regions = analyze_layout(page_img.image_bytes)
        text_regions = [r for r in regions if r.region_type == "text"]
        image_regions_meta = [r for r in regions if r.region_type == "image"]

        text_columns: list[TextColumn] = []
        for region in text_regions:
            raw_chars = recognize_region_safe(
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
    return all_pages


def emit_typ_and_pdf(
    all_pages,
    output_pdf: str,
    config: dict,
    layout: str,
    flow: bool,
    typ_only: bool = False,
    typ_path: str | None = None,
) -> str:
    from modules.pdf_writer import create_pdf
    from modules.typst_writer import build_typ_output_path

    writer = _pick_typst_writer(layout, flow)
    if typ_path is None:
        typ_path = build_typ_output_path(output_pdf)

    if layout == "horizontal":
        mode = "简体横排流式段落" if flow else "简体横排绝对坐标"
    else:
        mode = "流式grid竖排" if flow else "绝对坐标竖排"
    log.info(f"生成 Typst 源文件（{mode}）: {typ_path}")
    writer(all_pages, typ_path, config)
    log.info(f"Typst 源文件: {os.path.abspath(typ_path)}")
    if typ_only:
        return typ_path

    log.info(f"编译 PDF: {output_pdf}")
    ok = _compile_typ_to_pdf(typ_path, output_pdf)
    if not ok:
        log.warning("typst 编译失败，降级使用 ReportLab")
        create_pdf(all_pages, output_pdf, config)
    log.info(f"完成！输出文件: {os.path.abspath(output_pdf)}")
    return output_pdf


def process_images(
    inputs: list[str],
    output_pdf: str,
    config_path: str,
    dpi: int,
    confidence_threshold: float,
    page_start: int | None,
    page_end: int | None,
    layout_arg: str,
    flow: bool | None,
) -> None:
    from modules.image_reader import collect_image_paths, images_to_pages
    from modules.pdf_writer import load_config
    from modules.ocr_cache import save_ocr_cache, cache_path_for

    config = load_config(config_path)
    layout = resolve_layout(layout_arg, config)
    flow = resolve_flow(flow, layout)

    paths = collect_image_paths(inputs)
    page_range_desc = (
        f"第 {page_start}~{page_end} 页" if page_start or page_end else "全部"
    )
    log.info(f"读取图片 {len(paths)} 张  [{page_range_desc}]  排版={layout}")
    page_images = images_to_pages(
        paths, dpi=dpi, page_start=page_start, page_end=page_end,
    )
    log.info(f"共处理 {len(page_images)} 页")

    all_pages = ocr_pages_from_images(page_images, confidence_threshold, dpi)

    cache_file = cache_path_for(output_pdf)
    save_ocr_cache(all_pages, cache_file)
    log.info(f"OCR 缓存已保存: {os.path.abspath(cache_file)}")

    emit_typ_and_pdf(all_pages, output_pdf, config, layout, flow)


def process_from_cache(
    cache_path: str,
    output_pdf: str,
    config_path: str,
    layout_arg: str,
    flow: bool | None,
    typ_only: bool = False,
) -> None:
    from modules.ocr_cache import load_ocr_cache
    from modules.pdf_writer import load_config

    config = load_config(config_path)
    layout = resolve_layout(layout_arg, config)
    flow = resolve_flow(flow, layout)
    log.info(f"读取 OCR 缓存: {cache_path}")
    all_pages = load_ocr_cache(cache_path)
    log.info(f"共 {len(all_pages)} 页  排版={layout}")
    emit_typ_and_pdf(
        all_pages, output_pdf, config, layout, flow, typ_only=typ_only,
    )


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        page_start, page_end = parse_pages(args.pages)
    except ValueError as e:
        log.error(str(e))
        return 1

    source_for_name = args.inputs[0] if args.inputs else (args.from_cache or "output")
    output_pdf = build_output_path(source_for_name, args.output_pdf)
    log.info(f"输出路径: {output_pdf}")

    try:
        if args.pdf_from_typ:
            from main import compile_pdf_from_typ
            out_pdf = build_output_path(args.pdf_from_typ, args.output_pdf) if args.output_pdf else None
            compile_pdf_from_typ(args.pdf_from_typ, out_pdf)
        elif args.from_cache:
            process_from_cache(
                cache_path=args.from_cache,
                output_pdf=output_pdf,
                config_path=args.config,
                layout_arg=args.layout,
                flow=args.flow,
                typ_only=args.typ_only,
            )
        else:
            if not args.inputs:
                log.error("请提供图片路径/目录，或使用 --from-cache / --pdf-from-typ")
                return 1
            process_images(
                inputs=args.inputs,
                output_pdf=output_pdf,
                config_path=args.config,
                dpi=args.dpi,
                confidence_threshold=args.confidence,
                page_start=page_start,
                page_end=page_end,
                layout_arg=args.layout,
                flow=args.flow,
            )
    except Exception as e:
        log.error(f"处理失败: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
