"""Patch main.py:
  1. Remove duplicate _compile_typ_to_pdf
  2. Add --typ-only and --pdf-from-typ arguments
  3. Add generate_typ_only() and compile_pdf_from_typ() functions
  4. Wire new args into __main__ dispatch
"""
import pathlib, re

p = pathlib.Path('main.py')
src = p.read_text(encoding='utf-8')

# ── 1. Remove the first (duplicate) _compile_typ_to_pdf block ────────────────
marker = 'def _compile_typ_to_pdf('
first  = src.find(marker)
second = src.find(marker, first + 10)
if second != -1:
    # find the end of the first def block (next blank line after 'return False')
    end_of_first = src.find('\n\n\ndef ', first)
    if end_of_first == -1:
        end_of_first = src.find('\n\ndef ', first)
    src = src[:first] + src[second:]
    print('  [OK] removed duplicate _compile_typ_to_pdf')
else:
    print('  [skip] no duplicate _compile_typ_to_pdf found')

# ── 2. Update epilog in parse_args ───────────────────────────────────────────
old_epilog = (
    '            "示例:\\n"\n'
    '            "  python main.py input/古籍.pdf\\n"\n'
    '            "  python main.py input/古籍.pdf --pages 3-10\\n"\n'
    '            "  python main.py input/古籍.pdf --output 结果.pdf --pages 1-50\\n"'
)
new_epilog = (
    '            "示例:\\n"\n'
    '            "  # 完整流程：OCR → typ → PDF\\n"\n'
    '            "  python main.py input/古籍.pdf --pages 3-10\\n"\n'
    '            "\\n"\n'
    '            "  # 从 OCR 缓存只生成 typ（不编译 PDF）\\n"\n'
    '            "  python main.py --from-cache output/xxx.ocr.json --typ-only\\n"\n'
    '            "\\n"\n'
    '            "  # 从 typ 文件编译 PDF\\n"\n'
    '            "  python main.py --pdf-from-typ output/xxx.typ\\n"\n'
    '            "\\n"\n'
    '            "  # 从 OCR 缓存重新生成 typ + PDF\\n"\n'
    '            "  python main.py --from-cache output/xxx.ocr.json --output 结果.pdf\\n"'
)
src = src.replace(old_epilog, new_epilog)

# ── 3. Add --typ-only and --pdf-from-typ after --from-cache block ────────────
old_return = (
    '        "--from-cache",\n'
    '        dest="from_cache",\n'
    '        default=None,\n'
    '        metavar="FILE.ocr.json",\n'
    '        help="\u8df3\u8fc7 OCR\uff0c\u76f4\u63a5\u4ece\u7f13\u5b58\u6587\u4ef6\u91cd\u65b0\u751f\u6210 PDF \u548c Typst \u6e90\u6587\u4ef6",\n'
    '    )\n'
    '    return parser.parse_args(argv)'
)
new_return = (
    '        "--from-cache",\n'
    '        dest="from_cache",\n'
    '        default=None,\n'
    '        metavar="FILE.ocr.json",\n'
    '        help="\u8df3\u8fc7 OCR\uff0c\u76f4\u63a5\u4ece\u7f13\u5b58\u6587\u4ef6\u91cd\u65b0\u751f\u6210 PDF \u548c Typst \u6e90\u6587\u4ef6",\n'
    '    )\n'
    '    parser.add_argument(\n'
    '        "--typ-only",\n'
    '        dest="typ_only",\n'
    '        action="store_true",\n'
    '        default=False,\n'
    '        help="\u4e0e --from-cache \u914d\u5408\uff1a\u53ea\u751f\u6210 .typ \u6e90\u6587\u4ef6\uff0c\u4e0d\u7f16\u8bd1 PDF",\n'
    '    )\n'
    '    parser.add_argument(\n'
    '        "--pdf-from-typ",\n'
    '        dest="pdf_from_typ",\n'
    '        default=None,\n'
    '        metavar="FILE.typ",\n'
    '        help="\u76f4\u63a5\u4ece .typ \u6587\u4ef6\u7f16\u8bd1\u751f\u6210 PDF\uff08\u65e0\u9700 OCR\uff09",\n'
    '    )\n'
    '    return parser.parse_args(argv)'
)
src = src.replace(old_return, new_return)

# ── 4. Add generate_typ_only() and compile_pdf_from_typ() before process() ───
old_process_start = 'def process(\n    input_pdf: str,'
new_fns = '''\
def generate_typ_only(
    cache_path: str,
    typ_path: str | None = None,
    config_path: str = "config/layout_config.yaml",
) -> str:
    """从 .ocr.json 缓存只生成 .typ 文件，不编译 PDF。
    返回生成的 .typ 文件路径。
    """
    from modules.ocr_cache import load_ocr_cache
    from modules.pdf_writer import load_config
    from modules.typst_writer import create_typst, build_typ_output_path

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

    log.info(f"生成 Typst 源文件: {typ_path}")
    create_typst(all_pages, typ_path, config)
    log.info(f"完成！Typst 文件: {os.path.abspath(typ_path)}")
    return typ_path


def compile_pdf_from_typ(typ_path: str, output_pdf: str | None = None) -> str:
    """从 .typ 文件编译生成 PDF。
    返回生成的 PDF 文件路径。
    """
    if output_pdf is None:
        output_pdf = str(pathlib.Path(typ_path).with_suffix('.pdf'))

    log.info(f"编译: {typ_path}  →  {output_pdf}")
    ok = _compile_typ_to_pdf(typ_path, output_pdf)
    if not ok:
        log.error("typst 编译失败，且无 ReportLab 降级路径（需要 OCR 数据才能降级）")
        raise RuntimeError(f"typst 编译失败: {typ_path}")
    log.info(f"完成！PDF 文件: {os.path.abspath(output_pdf)}")
    return output_pdf


def process(
    input_pdf: str,'''
src = src.replace(old_process_start, new_fns)

# ── 5. Add pathlib import if not present ─────────────────────────────────────
if 'import pathlib' not in src:
    src = src.replace('import os\n', 'import os\nimport pathlib\n')

# ── 6. Wire new args in __main__ dispatch ────────────────────────────────────
old_dispatch = (
    '    try:\n'
    '        if args.from_cache:\n'
    '            process_from_cache(\n'
    '                cache_path=args.from_cache,\n'
    '                output_pdf=output_pdf,\n'
    '                config_path=args.config,\n'
    '            )\n'
    '        else:\n'
    '            if not args.input_pdf:\n'
    '                log.error("\u8bf7\u63d0\u4f9b\u6e90 PDF \u8def\u5f84\uff0c\u6216\u4f7f\u7528 --from-cache \u6307\u5b9a\u7f13\u5b58\u6587\u4ef6")\n'
    '                sys.exit(1)\n'
    '            process(\n'
    '                input_pdf=args.input_pdf,\n'
    '                output_pdf=output_pdf,\n'
    '                config_path=args.config,\n'
    '                dpi=args.dpi,\n'
    '                confidence_threshold=args.confidence,\n'
    '                page_start=page_start,\n'
    '                page_end=page_end,\n'
    '            )\n'
    '    except Exception as e:\n'
    '        log.error(f"\u5904\u7406\u5931\u8d25: {e}")\n'
    '        sys.exit(1)'
)
new_dispatch = (
    '    try:\n'
    '        if args.pdf_from_typ:\n'
    '            # \u6a21\u5f0f A\uff1a\u76f4\u63a5\u4ece .typ \u7f16\u8bd1 PDF\n'
    '            compile_pdf_from_typ(\n'
    '                typ_path=args.pdf_from_typ,\n'
    '                output_pdf=args.output_pdf,\n'
    '            )\n'
    '        elif args.from_cache and args.typ_only:\n'
    '            # \u6a21\u5f0f B\uff1a\u4ece OCR \u7f13\u5b58\u53ea\u751f\u6210 typ\n'
    '            generate_typ_only(\n'
    '                cache_path=args.from_cache,\n'
    '                typ_path=args.output_pdf,   # \u7528 --output \u6307\u5b9a typ \u8def\u5f84\uff08\u53ef\u9009\uff09\n'
    '                config_path=args.config,\n'
    '            )\n'
    '        elif args.from_cache:\n'
    '            # \u6a21\u5f0f C\uff1a\u4ece OCR \u7f13\u5b58\u751f\u6210 typ + PDF\n'
    '            process_from_cache(\n'
    '                cache_path=args.from_cache,\n'
    '                output_pdf=output_pdf,\n'
    '                config_path=args.config,\n'
    '            )\n'
    '        else:\n'
    '            # \u6a21\u5f0f D\uff1a\u5b8c\u6574\u6d41\u7a0b OCR \u2192 typ \u2192 PDF\n'
    '            if not args.input_pdf:\n'
    '                log.error("\u8bf7\u63d0\u4f9b\u6e90 PDF \u8def\u5f84\uff0c\u6216\u4f7f\u7528 --from-cache / --pdf-from-typ")\n'
    '                sys.exit(1)\n'
    '            process(\n'
    '                input_pdf=args.input_pdf,\n'
    '                output_pdf=output_pdf,\n'
    '                config_path=args.config,\n'
    '                dpi=args.dpi,\n'
    '                confidence_threshold=args.confidence,\n'
    '                page_start=page_start,\n'
    '                page_end=page_end,\n'
    '            )\n'
    '    except Exception as e:\n'
    '        log.error(f"\u5904\u7406\u5931\u8d25: {e}")\n'
    '        sys.exit(1)'
)
src = src.replace(old_dispatch, new_dispatch)

# ── verify ────────────────────────────────────────────────────────────────────
import ast
checks = [
    ('no dup _compile_typ_to_pdf',    src.count('def _compile_typ_to_pdf(') == 1),
    ('--typ-only arg',                '--typ-only' in src),
    ('--pdf-from-typ arg',            '--pdf-from-typ' in src),
    ('generate_typ_only fn',          'def generate_typ_only(' in src),
    ('compile_pdf_from_typ fn',       'def compile_pdf_from_typ(' in src),
    ('dispatch pdf_from_typ branch',  'args.pdf_from_typ' in src),
    ('dispatch typ_only branch',      'args.typ_only' in src),
    ('syntax ok',                     True),  # filled below
]
try:
    ast.parse(src)
    checks[-1] = ('syntax ok', True)
except SyntaxError as e:
    checks[-1] = ('syntax ok', False)
    print(f'  SYNTAX ERROR: {e}')

all_ok = True
for name, ok in checks:
    print(f'  [{"OK" if ok else "FAIL"}] {name}')
    if not ok: all_ok = False

if all_ok:
    p.write_text(src, encoding='utf-8', newline='\r\n')
    print('\nOK: main.py patched')
else:
    print('\nERROR: patch failed – file NOT written')
