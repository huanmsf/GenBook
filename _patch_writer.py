"""Patch main.py: replace ReportLab PDF with typst.compile() as primary output."""
import pathlib

p = pathlib.Path('main.py')
src = p.read_text(encoding='utf-8')
orig = src

# ── 1. Add _compile_typ_to_pdf() helper before process() ─────────────────────
old_process_def = 'def process(\n    input_pdf: str,'
new_helper_and_process = '''\
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


def process(
    input_pdf: str,'''
src = src.replace(old_process_def, new_helper_and_process)

# ── 2. In process(): replace create_pdf with typ→compile, keep ReportLab fallback ──
old_gen_pdf_block = '''\
    log.info(f"生成 PDF: {output_pdf}")
    create_pdf(all_pages, output_pdf, config)
    log.info(f"完成！输出文件: {os.path.abspath(output_pdf)}")

    # 保存 OCR 缓存（.ocr.json），可用 --from-cache 重新生成
    from modules.ocr_cache import save_ocr_cache, cache_path_for
    cache_file = cache_path_for(output_pdf)
    save_ocr_cache(all_pages, cache_file)
    log.info(f"OCR 缓存已保存: {os.path.abspath(cache_file)}")

    # 同步生成 Typst 源文件（与 PDF 同目录，扩展名 .typ）
    typ_path = build_typ_output_path(output_pdf)
    log.info(f"生成 Typst 源文件: {typ_path}")
    create_typst(all_pages, typ_path, config)
    log.info(f"完成！Typst 文件: {os.path.abspath(typ_path)}")
    log.info(f"  编译为 PDF: typst compile \\"{os.path.abspath(typ_path)}\\"")'''

new_gen_pdf_block = '''\
    # 保存 OCR 缓存（.ocr.json），可用 --from-cache 重新生成
    from modules.ocr_cache import save_ocr_cache, cache_path_for
    cache_file = cache_path_for(output_pdf)
    save_ocr_cache(all_pages, cache_file)
    log.info(f"OCR 缓存已保存: {os.path.abspath(cache_file)}")

    # 生成 Typst 源文件
    typ_path = build_typ_output_path(output_pdf)
    log.info(f"生成 Typst 源文件: {typ_path}")
    create_typst(all_pages, typ_path, config)
    log.info(f"Typst 源文件: {os.path.abspath(typ_path)}")

    # 主路：typst.compile() → PDF（与 typ 样式一致）
    log.info(f"编译 PDF: {output_pdf}")
    ok = _compile_typ_to_pdf(typ_path, output_pdf)
    if not ok:
        # 降级：ReportLab（布局较简陋，仅供应急）
        log.warning("降级使用 ReportLab 生成 PDF（布局与 Typst 不同）")
        create_pdf(all_pages, output_pdf, config)
    log.info(f"完成！输出文件: {os.path.abspath(output_pdf)}")'''

src = src.replace(old_gen_pdf_block, new_gen_pdf_block)

# ── 3. In process_from_cache(): same replacement ─────────────────────────────
old_cache_pdf_block = '''\
    log.info(f"生成 PDF: {output_pdf}")
    create_pdf(all_pages, output_pdf, config)
    log.info(f"完成！输出文件: {os.path.abspath(output_pdf)}")

    typ_path = build_typ_output_path(output_pdf)
    log.info(f"生成 Typst 源文件: {typ_path}")
    create_typst(all_pages, typ_path, config)
    log.info(f"完成！Typst 文件: {os.path.abspath(typ_path)}")
    log.info(f"  编译为 PDF: typst compile \\"{os.path.abspath(typ_path)}\\"")'''

new_cache_pdf_block = '''\
    # 生成 Typst 源文件
    typ_path = build_typ_output_path(output_pdf)
    log.info(f"生成 Typst 源文件: {typ_path}")
    create_typst(all_pages, typ_path, config)
    log.info(f"Typst 源文件: {os.path.abspath(typ_path)}")

    # 主路：typst.compile() → PDF
    log.info(f"编译 PDF: {output_pdf}")
    ok = _compile_typ_to_pdf(typ_path, output_pdf)
    if not ok:
        log.warning("降级使用 ReportLab 生成 PDF")
        create_pdf(all_pages, output_pdf, config)
    log.info(f"完成！输出文件: {os.path.abspath(output_pdf)}")'''

src = src.replace(old_cache_pdf_block, new_cache_pdf_block)

# ── verify ────────────────────────────────────────────────────────────────────
checks = [
    ('_compile_typ_to_pdf defined',   'def _compile_typ_to_pdf(' in src),
    ('typst.compile() call',          'pdf_bytes = _typst.compile(typ_path)' in src),
    ('process uses _compile',         '_compile_typ_to_pdf(typ_path, output_pdf)' in src),
    ('process_from_cache uses _compile', src.count('_compile_typ_to_pdf(typ_path, output_pdf)') == 2),
    ('ReportLab still as fallback',   "降级使用 ReportLab 生成 PDF" in src),
]
all_ok = True
for name, ok in checks:
    print(f'  [{"OK" if ok else "FAIL"}] {name}')
    if not ok: all_ok = False

if all_ok:
    p.write_text(src, encoding='utf-8', newline='\r\n')
    print('\nOK: main.py patched – typst.compile() is now primary PDF output')
else:
    print('\nERROR: patch failed – file NOT written')
