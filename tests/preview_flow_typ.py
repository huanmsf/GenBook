"""tests/preview_flow_typ.py
将"绝对坐标版" .typ 转为"流式 grid 竖排版" .typ，用于预览效果。

核心思路
--------
绝对坐标版（原版）：
    每列用 #place(top+left, dx: Xpt, dy: Ypt, box(...)[#vcol(...)])
    坐标硬编码，移列须逐一改 dx

流式版（本脚本生成）：
    #set page(...)  #set text(...)  — 与原版相同
    每页用一个 #grid(columns: ..., column-gutter: ...) 包含所有列
    列顺序即显示顺序，插列/删列/换页只需增删 grid 的子项

使用方法
--------
    # 最简（输出到 output/xxx_flow.typ）
    python tests/preview_flow_typ.py output/xxx.typ

    # 指定输出
    python tests/preview_flow_typ.py output/xxx.typ --out output/xxx_flow.typ

    # 同时编译为 PDF（需要 pip install typst）
    python tests/preview_flow_typ.py output/xxx.typ --compile

流式版的编辑优势
---------------
1. 整体左移 N 列：删掉最右侧 N 个 grid 子项，后续列自动填位
2. 插入空列：在 grid 中插入 []（空格占位）
3. 最后几列移到下一页：剪切 grid 子项，粘贴到下一页 grid 开头
4. 列首字下沉：修改 pad(top: Xpt) 中的数值即可

局限说明
--------
- 列内 dy（首字下沉）用 pad(top: dy) 模拟，与绝对坐标版略有差异
  （这正是"预览"脚本的意义：先看效果再决定是否全面迁移）
- 图片列（#image(...)）原样保留
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class ColEntry:
    """一列的内容，从 #place 行解析而来。"""
    col_idx: int           # 列序号（注释里的"列 N"）
    col_type: str          # main / note / title / image
    char_count: int        # 字数
    dx_pt: float           # 原始 dx（pt）
    dy_pt: float           # 原始 dy（pt）
    fw_var: str            # 字号变量名，如 "cw" / "title_fw"
    text: str              # 文字内容（image 列则为图片路径）
    raw_box: str           # 原始 box 字符串（兜底保留）


@dataclass
class PageEntry:
    """一页数据。"""
    page_num: int
    block_w_pt: float
    block_h_pt: float
    binding: str
    cols: list[ColEntry] = field(default_factory=list)
    is_empty: bool = False


# ---------------------------------------------------------------------------
# 解析器
# ---------------------------------------------------------------------------

_RE_PAGE_HEADER = re.compile(
    r'//\s*===\s*第\s*(\d+)\s*页.*?版心=(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)pt.*?装订=(.*?)\s*==='
)
_RE_COL_COMMENT = re.compile(
    r'//\s*列\s*(\d+):\s*(\w+)\s+字数=\s*(\d+)\s+cx=\d+px\s+x_left=([\d.]+)pt\s+dy=([\d.]+)pt'
)
_RE_PLACE = re.compile(
    r'#place\(top \+ left,\s*dx:\s*([\d.]+)pt,\s*dy:\s*([\d.]+)pt,\s*'
    r'box\(width:\s*([^,]+),\s*height:\s*[\d.]+pt\)'
    r'\[#vcol\("([^"]*)",\s*fw:\s*([^)]+)\)\]'
    r'\)'
)
_RE_PLACE_IMAGE = re.compile(
    r'#place\(top \+ left,\s*dx:\s*([\d.]+)pt,\s*dy:\s*([\d.]+)pt,\s*'
    r'box\(width:\s*[^,]+,\s*height:\s*[\d.]+pt\)'
    r'\[#image\("([^"]+)"\)\]'
    r'\)'
)


def _parse_typ(src: str) -> tuple[str, list[PageEntry]]:
    """解析 .typ 源码，返回 (头部字符串, 页列表)。"""
    lines = src.splitlines()
    header_lines: list[str] = []
    pages: list[PageEntry] = []
    in_header = True
    current_page: PageEntry | None = None
    pending_col_meta: tuple | None = None

    for line in lines:
        # 页头注释
        m = _RE_PAGE_HEADER.search(line)
        if m:
            in_header = False
            if current_page is not None:
                pages.append(current_page)
            current_page = PageEntry(
                page_num=int(m.group(1)),
                block_w_pt=float(m.group(2)),
                block_h_pt=float(m.group(3)),
                binding=m.group(4).strip(),
            )
            pending_col_meta = None
            continue

        if in_header:
            header_lines.append(line)
            continue

        # 列注释（预读 meta）
        m = _RE_COL_COMMENT.search(line)
        if m and current_page is not None:
            pending_col_meta = (
                int(m.group(1)), m.group(2), int(m.group(3)),
                float(m.group(4)), float(m.group(5)),
            )
            continue

        # #place 内容行
        if '#place(' in line and current_page is not None:
            mi = _RE_PLACE_IMAGE.search(line)
            if mi:
                col = ColEntry(
                    col_idx=pending_col_meta[0] if pending_col_meta else 0,
                    col_type='image', char_count=0,
                    dx_pt=float(mi.group(1)), dy_pt=float(mi.group(2)),
                    fw_var='cw', text=mi.group(3), raw_box=line.strip(),
                )
                current_page.cols.append(col)
                pending_col_meta = None
                continue

            mv = _RE_PLACE.search(line)
            if mv:
                c_idx, c_type, c_chars = 0, 'main', len(mv.group(4))
                if pending_col_meta:
                    c_idx, c_type, c_chars = (
                        pending_col_meta[0], pending_col_meta[1], pending_col_meta[2],
                    )
                col = ColEntry(
                    col_idx=c_idx, col_type=c_type, char_count=c_chars,
                    dx_pt=float(mv.group(1)), dy_pt=float(mv.group(2)),
                    fw_var=mv.group(5).strip(), text=mv.group(4),
                    raw_box=line.strip(),
                )
                current_page.cols.append(col)
                pending_col_meta = None
                continue

        # （不再用 #block( 判断空页，改在 append 时根据 cols 动态判断）

    if current_page is not None:
        pages.append(current_page)

    # 没有列的页才是真空页
    for p in pages:
        if not p.cols:
            p.is_empty = True

    return '\n'.join(header_lines), pages


# ---------------------------------------------------------------------------
# 生成流式 .typ
# ---------------------------------------------------------------------------

_FLOW_BANNER = """\
// ╔══════════════════════════════════════════════════════════════════╗
// ║  GenBook 流式竖排版  (tests/preview_flow_typ.py 自动生成)        ║
// ║                                                                  ║
// ║  编辑指南：                                                      ║
// ║  · 每页是一个 #grid(...)，列顺序 = 显示顺序（右→左）            ║
// ║  · 插入空列：在 grid 中加一个 []                                 ║
// ║  · 删除/移动列：直接剪切 grid 子项到目标位置                     ║
// ║  · 列首字下沉（dy）：修改 pad(top: Xpt) 中的值                  ║
// ║  · 换页：把 grid 子项剪切到下一页的 grid 开头                    ║
// ║  · 起始位置：所有页统一 align(right)，内容从右侧书口起排列         ║
// ╚══════════════════════════════════════════════════════════════════╝
"""


def _col_item(col: ColEntry, col_h: float) -> str:
    """生成单列的 grid 子项。"""
    dy = col.dy_pt
    fw = col.fw_var
    label = f'// 列{col.col_idx}({col.col_type}) {col.char_count}字  dy={dy:.1f}pt'

    if col.col_type == 'image':
        inner = f'#image("{col.text}")'
    else:
        t = col.text.replace('"', '\\"')
        inner = f'#vcol("{t}", fw: {fw})'

    if dy > 0.5:
        body = f'box(height: {col_h:.1f}pt)[#pad(top: {dy:.1f}pt)[{inner}]]'
    else:
        body = f'box(height: {col_h:.1f}pt)[{inner}]'

    return f'{label}\n    {body}'


def _generate_flow_typ(header: str, pages: list[PageEntry],
                       col_spacing_pt: float = 5.0) -> str:
    out: list[str] = [_FLOW_BANNER.rstrip(), '']

    # 头部：过滤掉原版本注释行，保留 set/let/函数定义
    for ln in header.splitlines():
        if ln.startswith('// GenBook v'):
            continue
        out.append(ln)
    out.append('')

    for page in pages:
        pg = page.page_num
        sep = '=' * 64
        out.append(f'// {sep}')
        out.append(f'// 第 {pg} 页  装订={page.binding}')
        out.append(f'// {sep}')
        out.append('')

        if page.is_empty or not page.cols:
            out += [
                f'// （空页）',
                f'#block(width: {page.block_w_pt:.1f}pt, height: {page.block_h_pt:.1f}pt)[',
                f'  #place(bottom + center)[#text(size: pagenum_fw)[{pg}]]',
                f']',
                '#pagebreak()',
                '',
            ]
            continue

        n = len(page.cols)
        col_h = page.block_h_pt

        # OCR 列按 dx 降序排列（右→左）；grid 子项须按 dx 升序（物理左→右）
        # 配合 #align(right/left) 后，视觉顺序与原版完全一致
        sorted_cols = sorted(page.cols, key=lambda c: c.dx_pt)  # 升序：左→右
        col_widths = ', '.join(f'({c.fw_var})' for c in sorted_cols)

        # 所有页统一从右起排列，右侧留白固定一致（不区分奇偶页）
        # 子项按 dx 升序（物理左→右），align(right) 后视觉从右书口向左展开

        out += [
            f'// 版心 {page.block_w_pt:.1f}×{page.block_h_pt:.1f}pt  共 {n} 列  右起排列',
            f'// 子项=物理左→右(dx小→大)；视觉从右起读；右侧留白固定',
            f'// 移列：剪切子项到目标位置；插空列：加 []；换页：移到下页grid开头',
            f'#block(width: {page.block_w_pt:.1f}pt, height: {page.block_h_pt:.1f}pt)[',
            f'  #place(bottom + center)[#text(size: pagenum_fw)[{pg}]]',
            f'  #align(right)[  // 统一：内容从右侧起排，右边留白一致',
            f'  #grid(',
            f'    columns: ({col_widths}),',
            f'    column-gutter: {col_spacing_pt:.1f}pt,',
            f'    align: top,',
        ]

        items = [_col_item(c, col_h) for c in sorted_cols]
        for idx, item in enumerate(items):
            comma = ',' if idx < len(items) - 1 else ''
            item_lines = item.splitlines()
            for li, il in enumerate(item_lines):
                out.append(f'    {il}')
            out[-1] += comma

        out += [
            f'  )  // end grid p{pg}',
            f'  ]  // end align right',
            f']',
            '#pagebreak()',
            '',
        ]

    return '\n'.join(out)


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description='将绝对坐标 .typ 转换为流式 grid 竖排 .typ（预览用）',
        epilog="""
示例:
  python tests/preview_flow_typ.py output/book.typ
  python tests/preview_flow_typ.py output/book.typ --out output/book_flow.typ
  python tests/preview_flow_typ.py output/book.typ --compile
        """,
    )
    parser.add_argument('src', help='源 .typ 文件路径（绝对坐标版）')
    parser.add_argument('--out', default=None,
                        help='输出路径（默认：源文件名加 _flow.typ）')
    parser.add_argument('--col-spacing', type=float, default=5.0,
                        help='列间距 pt（默认 5.0）')
    parser.add_argument('--compile', action='store_true',
                        help='生成后用 typst 包编译为 PDF（需 pip install typst）')
    args = parser.parse_args(argv)

    src_path = pathlib.Path(args.src)
    if not src_path.exists():
        print(f'ERROR: 文件不存在: {src_path}', file=sys.stderr)
        sys.exit(1)

    out_path = (pathlib.Path(args.out) if args.out
                else src_path.with_stem(src_path.stem + '_flow'))

    print(f'读取: {src_path}')
    src_text = src_path.read_text(encoding='utf-8')

    print('解析绝对坐标版 .typ ...')
    header, pages = _parse_typ(src_text)
    total_cols = sum(len(p.cols) for p in pages)
    print(f'  共 {len(pages)} 页，{total_cols} 列')

    print('生成流式版 .typ ...')
    flow_src = _generate_flow_typ(header, pages, col_spacing_pt=args.col_spacing)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(flow_src, encoding='utf-8', newline='\r\n')
    print(f'已写出: {out_path}  ({len(flow_src.splitlines())} 行)')

    # 统计
    empty_pages = [p for p in pages if p.is_empty or not p.cols]
    col_types: dict[str, int] = {}
    for p in pages:
        for c in p.cols:
            col_types[c.col_type] = col_types.get(c.col_type, 0) + 1
    print(f'\n统计:  {len(pages)} 页  空页={[p.page_num for p in empty_pages]}')
    for t, n in sorted(col_types.items()):
        print(f'  {t:8s}: {n} 列')

    if args.compile:
        print('\n编译为 PDF ...')
        try:
            import typst as _typst
            pdf_path = out_path.with_suffix('.pdf')
            pdf_path.write_bytes(_typst.compile(str(out_path)))
            print(f'PDF: {pdf_path}')
        except ImportError:
            print('警告: typst 包未安装，跳过（pip install typst）')
        except Exception as e:
            print(f'编译失败: {e}')

    print(f'\n完成。用 Tinymist 打开预览：\n  {out_path}')


if __name__ == '__main__':
    main()
