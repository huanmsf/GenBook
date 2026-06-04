"""Patch main.py: add --flow/--no-flow, update epilog, wire flow param"""
import pathlib
src = pathlib.Path('main.py').read_bytes().decode('utf-8')

# ── 1. 替换 epilog ────────────────────────────────────────────────────────
old_epilog = (
    '        epilog=(\r\n'
    '            "示例:\\n"\r\n'
    '            "  # 完整流程：OCR \u2192 typ \u2192 PDF\\n"\r\n'
    '            "  python main.py input/古籍.pdf --pages 3-10\\n"\r\n'
    '            "\\n"\r\n'
    '            "  # 从 OCR 缓存只生成 typ（不编译 PDF）\\n"\r\n'
    '            "  python main.py --from-cache output/xxx.ocr.json --typ-only\\n"\r\n'
    '            "\\n"\r\n'
    '            "  # 从 typ 文件编译 PDF\\n"\r\n'
    '            "  python main.py --pdf-from-typ output/xxx.typ\\n"\r\n'
    '            "\\n"\r\n'
    '            "  # 从 OCR 缓存重新生成 typ + PDF\\n"\r\n'
    '            "  python main.py --from-cache output/xxx.ocr.json --output 结果.pdf\\n"\r\n'
    '        ),\r\n'
)
new_epilog = (
    '        epilog=(\r\n'
    '            "排版模式:\\n"\r\n'
    '            "  --flow      (默认) 流式 grid 竖排：列顺序即显示顺序，插删列只需增删 grid 子项\\n"\r\n'
    '            "  --no-flow   绝对坐标竖排：每列用 #place(dx,dy) 精确定位，移列须逐一改坐标\\n"\r\n'
    '            "\\n"\r\n'
    '            "示例:\\n"\r\n'
    '            "  # 完整流程：OCR \u2192 流式 typ \u2192 PDF（默认流式模式）\\n"\r\n'
    '            "  python main.py input/古籍.pdf --pages 3-10\\n"\r\n'
    '            "\\n"\r\n'
    '            "  # 完整流程：使用绝对坐标模式\\n"\r\n'
    '            "  python main.py input/古籍.pdf --pages 3-10 --no-flow\\n"\r\n'
    '            "\\n"\r\n'
    '            "  # 从 OCR 缓存只生成流式 typ（不编译 PDF）\\n"\r\n'
    '            "  python main.py --from-cache output/xxx.ocr.json --typ-only\\n"\r\n'
    '            "\\n"\r\n'
    '            "  # 从 OCR 缓存只生成绝对坐标 typ\\n"\r\n'
    '            "  python main.py --from-cache output/xxx.ocr.json --typ-only --no-flow\\n"\r\n'
    '            "\\n"\r\n'
    '            "  # 从 OCR 缓存重新生成流式 typ + PDF\\n"\r\n'
    '            "  python main.py --from-cache output/xxx.ocr.json --output 结果.pdf\\n"\r\n'
    '            "\\n"\r\n'
    '            "  # 从 typ 文件编译 PDF\\n"\r\n'
    '            "  python main.py --pdf-from-typ output/xxx.typ\\n"\r\n'
    '        ),\r\n'
)
assert old_epilog in src, f'MISS epilog'
src = src.replace(old_epilog, new_epilog, 1)

# ── 2. 在 --pdf-from-typ 参数后加 --flow / --no-flow ─────────────────────
old_pft_end = (
    '        help="直接从 .typ 文件编译生成 PDF（无需 OCR）",\r\n'
    '    )\r\n'
    '    return parser.parse_args(argv)\r\n'
)
new_pft_end = (
    '        help="直接从 .typ 文件编译生成 PDF（无需 OCR）",\r\n'
    '    )\r\n'
    '    parser.add_argument(\r\n'
    '        "--flow",\r\n'
    '        dest="flow",\r\n'
    '        action="store_true",\r\n'
    '        default=True,\r\n'
    '        help="使用流式 grid 竖排模式生成 .typ（默认开启）",\r\n'
    '    )\r\n'
    '    parser.add_argument(\r\n'
    '        "--no-flow",\r\n'
    '        dest="flow",\r\n'
    '        action="store_false",\r\n'
    '        help="使用绝对坐标竖排模式生成 .typ（回退到 typst_writer）",\r\n'
    '    )\r\n'
    '    return parser.parse_args(argv)\r\n'
)
assert old_pft_end in src, f'MISS pft_end'
src = src.replace(old_pft_end, new_pft_end, 1)

# ── 3. generate_typ_only 签名 + import + 调用 ────────────────────────────
old_gto_sig = (
    'def generate_typ_only(\r\n'
    '    cache_path: str,\r\n'
    '    typ_path: str | None = None,\r\n'
    '    config_path: str = "config/layout_config.yaml",\r\n'
    ') -> str:\r\n'
    '    """从 .ocr.json 缓存只生成 .typ 文件，不编译 PDF。\r\n'
    '    返回生成的 .typ 文件路径。\r\n'
    '    """\r\n'
    '    from modules.ocr_cache import load_ocr_cache\r\n'
    '    from modules.pdf_writer import load_config\r\n'
    '    from modules.typst_writer import create_typst, build_typ_output_path\r\n'
)
new_gto_sig = (
    'def generate_typ_only(\r\n'
    '    cache_path: str,\r\n'
    '    typ_path: str | None = None,\r\n'
    '    config_path: str = "config/layout_config.yaml",\r\n'
    '    flow: bool = True,\r\n'
    ') -> str:\r\n'
    '    """从 .ocr.json 缓存只生成 .typ 文件，不编译 PDF。\r\n'
    '    返回生成的 .typ 文件路径。\r\n'
    '    flow=True（默认）流式 grid 竖排；flow=False 绝对坐标竖排。\r\n'
    '    """\r\n'
    '    from modules.ocr_cache import load_ocr_cache\r\n'
    '    from modules.pdf_writer import load_config\r\n'
    '    from modules.typst_flow_writer import create_typst\r\n'
    '    from modules.typst_writer import build_typ_output_path\r\n'
)
assert old_gto_sig in src, f'MISS gto_sig'
src = src.replace(old_gto_sig, new_gto_sig, 1)

old_gto_gen = (
    '    log.info(f"生成 Typst 源文件: {typ_path}")\r\n'
    '    create_typst(all_pages, typ_path, config)\r\n'
    '    log.info(f"完成！Typst 文件: {os.path.abspath(typ_path)}")\r\n'
    '    return typ_path\r\n'
    '\r\n'
    '\r\n'
    'def compile_pdf_from_typ'
)
new_gto_gen = (
    '    mode = "流式grid" if flow else "绝对坐标"\r\n'
    '    log.info(f"生成 Typst 源文件（{mode}模式）: {typ_path}")\r\n'
    '    create_typst(all_pages, typ_path, config, flow=flow)\r\n'
    '    log.info(f"完成！Typst 文件: {os.path.abspath(typ_path)}")\r\n'
    '    return typ_path\r\n'
    '\r\n'
    '\r\n'
    'def compile_pdf_from_typ'
)
assert old_gto_gen in src, f'MISS gto_gen'
src = src.replace(old_gto_gen, new_gto_gen, 1)

# ── 4. process() 签名 + import + 调用 ────────────────────────────────────
old_proc_sig = (
    'def process(\r\n'
    '    input_pdf: str,\r\n'
    '    output_pdf: str,\r\n'
    '    config_path: str = "config/layout_config.yaml",\r\n'
    '    dpi: int = 300,\r\n'
    '    confidence_threshold: float = 0.7,\r\n'
    '    page_start: int | None = None,\r\n'
    '    page_end: int | None = None,\r\n'
    ') -> None:\r\n'
    '    """主处理流程：读取 PDF \u2192 版面分析 \u2192 OCR \u2192 重构 PDF。"""\r\n'
)
new_proc_sig = (
    'def process(\r\n'
    '    input_pdf: str,\r\n'
    '    output_pdf: str,\r\n'
    '    config_path: str = "config/layout_config.yaml",\r\n'
    '    dpi: int = 300,\r\n'
    '    confidence_threshold: float = 0.7,\r\n'
    '    page_start: int | None = None,\r\n'
    '    page_end: int | None = None,\r\n'
    '    flow: bool = True,\r\n'
    ') -> None:\r\n'
    '    """主处理流程：读取 PDF \u2192 版面分析 \u2192 OCR \u2192 重构 PDF。\r\n'
    '    flow=True（默认）流式 grid 竖排；flow=False 绝对坐标竖排。\r\n'
    '    """\r\n'
)
assert old_proc_sig in src, f'MISS proc_sig'
src = src.replace(old_proc_sig, new_proc_sig, 1)

old_proc_import = (
    '    from modules.pdf_writer import load_config, create_pdf\r\n'
    '    from modules.typst_writer import create_typst, build_typ_output_path\r\n'
    '\r\n'
    '    config = load_config(config_path)\r\n'
    '\r\n'
    '    page_range_desc'
)
new_proc_import = (
    '    from modules.pdf_writer import load_config, create_pdf\r\n'
    '    from modules.typst_flow_writer import create_typst as _flow_create\r\n'
    '    from modules.typst_writer import create_typst as _abs_create, build_typ_output_path\r\n'
    '    _create_typst = _flow_create if flow else _abs_create\r\n'
    '\r\n'
    '    config = load_config(config_path)\r\n'
    '\r\n'
    '    page_range_desc'
)
assert old_proc_import in src, f'MISS proc_import'
src = src.replace(old_proc_import, new_proc_import, 1)

old_proc_gen = (
    '    # 生成 Typst 源文件\r\n'
    '    typ_path = build_typ_output_path(output_pdf)\r\n'
    '    log.info(f"生成 Typst 源文件: {typ_path}")\r\n'
    '    create_typst(all_pages, typ_path, config)\r\n'
    '    log.info(f"Typst 源文件: {os.path.abspath(typ_path)}")\r\n'
    '\r\n'
    '    # 主路：typst.compile() → PDF（与 typ 样式一致）\r\n'
)
new_proc_gen = (
    '    # 生成 Typst 源文件\r\n'
    '    typ_path = build_typ_output_path(output_pdf)\r\n'
    '    mode = "流式grid" if flow else "绝对坐标"\r\n'
    '    log.info(f"生成 Typst 源文件（{mode}模式）: {typ_path}")\r\n'
    '    _create_typst(all_pages, typ_path, config, flow=flow)\r\n'
    '    log.info(f"Typst 源文件: {os.path.abspath(typ_path)}")\r\n'
    '\r\n'
    '    # 主路：typst.compile() → PDF（与 typ 样式一致）\r\n'
)
assert old_proc_gen in src, f'MISS proc_gen'
src = src.replace(old_proc_gen, new_proc_gen, 1)

# ── 5. process_from_cache() 签名 + import + 调用 ─────────────────────────
old_pfc_sig = (
    'def process_from_cache(\r\n'
    '    cache_path: str,\r\n'
    '    output_pdf: str,\r\n'
    '    config_path: str = "config/layout_config.yaml",\r\n'
    ') -> None:\r\n'
    '    """从 .ocr.json 缓存直接生成 PDF 和 Typst 文件，无需重跑 OCR。"""\r\n'
    '    from modules.ocr_cache import load_ocr_cache\r\n'
    '    from modules.pdf_writer import load_config, create_pdf\r\n'
    '    from modules.typst_writer import create_typst, build_typ_output_path\r\n'
)
new_pfc_sig = (
    'def process_from_cache(\r\n'
    '    cache_path: str,\r\n'
    '    output_pdf: str,\r\n'
    '    config_path: str = "config/layout_config.yaml",\r\n'
    '    flow: bool = True,\r\n'
    ') -> None:\r\n'
    '    """从 .ocr.json 缓存直接生成 PDF 和 Typst 文件，无需重跑 OCR。\r\n'
    '    flow=True（默认）流式 grid 竖排；flow=False 绝对坐标竖排。\r\n'
    '    """\r\n'
    '    from modules.ocr_cache import load_ocr_cache\r\n'
    '    from modules.pdf_writer import load_config, create_pdf\r\n'
    '    from modules.typst_flow_writer import create_typst as _flow_create\r\n'
    '    from modules.typst_writer import create_typst as _abs_create, build_typ_output_path\r\n'
    '    _create_typst = _flow_create if flow else _abs_create\r\n'
)
assert old_pfc_sig in src, f'MISS pfc_sig'
src = src.replace(old_pfc_sig, new_pfc_sig, 1)

old_pfc_gen = (
    '    # 生成 Typst 源文件\r\n'
    '    typ_path = build_typ_output_path(output_pdf)\r\n'
    '    log.info(f"生成 Typst 源文件: {typ_path}")\r\n'
    '    create_typst(all_pages, typ_path, config)\r\n'
    '    log.info(f"Typst 源文件: {os.path.abspath(typ_path)}")\r\n'
    '\r\n'
    '    # 主路：typst.compile() → PDF\r\n'
)
new_pfc_gen = (
    '    # 生成 Typst 源文件\r\n'
    '    typ_path = build_typ_output_path(output_pdf)\r\n'
    '    mode = "流式grid" if flow else "绝对坐标"\r\n'
    '    log.info(f"生成 Typst 源文件（{mode}模式）: {typ_path}")\r\n'
    '    _create_typst(all_pages, typ_path, config, flow=flow)\r\n'
    '    log.info(f"Typst 源文件: {os.path.abspath(typ_path)}")\r\n'
    '\r\n'
    '    # 主路：typst.compile() → PDF\r\n'
)
assert old_pfc_gen in src, f'MISS pfc_gen'
src = src.replace(old_pfc_gen, new_pfc_gen, 1)

# ── 6. 入口：各调用处传入 flow=args.flow ─────────────────────────────────
old_call_gto = (
    '            generate_typ_only(\r\n'
    '                cache_path=args.from_cache,\r\n'
    '                typ_path=args.output_pdf,   # 用 --output 指定 typ 路径（可选）\r\n'
    '                config_path=args.config,\r\n'
    '            )\r\n'
)
new_call_gto = (
    '            generate_typ_only(\r\n'
    '                cache_path=args.from_cache,\r\n'
    '                typ_path=args.output_pdf,   # 用 --output 指定 typ 路径（可选）\r\n'
    '                config_path=args.config,\r\n'
    '                flow=args.flow,\r\n'
    '            )\r\n'
)
assert old_call_gto in src, f'MISS call_gto'
src = src.replace(old_call_gto, new_call_gto, 1)

old_call_pfc = (
    '            process_from_cache(\r\n'
    '                cache_path=args.from_cache,\r\n'
    '                output_pdf=output_pdf,\r\n'
    '                config_path=args.config,\r\n'
    '            )\r\n'
)
new_call_pfc = (
    '            process_from_cache(\r\n'
    '                cache_path=args.from_cache,\r\n'
    '                output_pdf=output_pdf,\r\n'
    '                config_path=args.config,\r\n'
    '                flow=args.flow,\r\n'
    '            )\r\n'
)
assert old_call_pfc in src, f'MISS call_pfc'
src = src.replace(old_call_pfc, new_call_pfc, 1)

old_call_proc = (
    '            process(\r\n'
    '                input_pdf=args.input_pdf,\r\n'
    '                output_pdf=output_pdf,\r\n'
    '                config_path=args.config,\r\n'
    '                dpi=args.dpi,\r\n'
    '                confidence_threshold=args.confidence,\r\n'
    '                page_start=page_start,\r\n'
    '                page_end=page_end,\r\n'
    '            )\r\n'
)
new_call_proc = (
    '            process(\r\n'
    '                input_pdf=args.input_pdf,\r\n'
    '                output_pdf=output_pdf,\r\n'
    '                config_path=args.config,\r\n'
    '                dpi=args.dpi,\r\n'
    '                confidence_threshold=args.confidence,\r\n'
    '                page_start=page_start,\r\n'
    '                page_end=page_end,\r\n'
    '                flow=args.flow,\r\n'
    '            )\r\n'
)
assert old_call_proc in src, f'MISS call_proc'
src = src.replace(old_call_proc, new_call_proc, 1)

pathlib.Path('main.py').write_bytes(src.encode('utf-8'))
print('ALL OK')
