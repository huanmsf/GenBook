"""
ocr_cache.py — 跑 OCR 并把结果序列化为 JSON，供后续调试复用。

用法：
    python ocr_cache.py               # 处理 E:/zywc.pdf 1-20页
    python ocr_cache.py --pages 1-5   # 只处理前5页
    python ocr_cache.py --inspect     # 只打印已有缓存内容（不重跑OCR）

输出：
    output/ocr_cache_zywc_p1-20.json
"""
from __future__ import annotations
import argparse, json, os, sys, re
sys.path.insert(0, os.path.dirname(__file__))


def run_ocr(pdf_path: str, page_start: int, page_end: int, dpi: int = 300) -> list[dict]:
    """跑完整 OCR 流程，返回可序列化的 list[page_dict]。"""
    from modules.pdf_reader import pdf_to_images
    from modules.layout_analyzer import analyze_layout, Region
    from modules.ocr_engine import recognize_region, sort_vertical_chars
    from modules.image_cropper import crop_image_region
    import warnings; warnings.filterwarnings("ignore")

    page_images = pdf_to_images(pdf_path, dpi=dpi,
                                page_start=page_start, page_end=page_end)
    print(f"共 {len(page_images)} 页需要处理")

    all_pages = []
    for pi in page_images:
        print(f"  OCR 第 {pi.page_num} 页 ...", flush=True)
        regions = analyze_layout(pi.image_bytes)
        text_regions = [r for r in regions if r.region_type == "text"]
        img_regions  = [r for r in regions if r.region_type == "image"]

        columns = []
        for r in text_regions:
            raw = recognize_region(pi.image_bytes, region_bbox=r.bbox,
                                   confidence_threshold=0.5)
            chars = sort_vertical_chars(raw)
            columns.append({
                "col_bbox": list(r.bbox),
                "chars": [
                    {"text": c.text,
                     "bbox": list(c.bbox),
                     "conf": round(float(c.confidence), 3)}
                    for c in chars
                ]
            })

        # 按列 bbox x 中心从大到小排序（从右到左）
        columns.sort(key=lambda c: -(c["col_bbox"][0] + c["col_bbox"][2]) / 2)
        for i, col in enumerate(columns):
            col["source_order"] = i + 1   # 1=最右

        all_pages.append({
            "page_num":        pi.page_num,
            "width_px":        pi.orig_width_px,
            "height_px":       pi.orig_height_px,
            "dpi":             dpi,
            "text_columns":    columns,
            "image_regions":   [{"bbox": list(r.bbox)} for r in img_regions],
        })

    return all_pages


def inspect_cache(data: list[dict]) -> None:
    """打印每页列结构详情，供对比原 PDF。"""
    for page in data:
        pn   = page["page_num"]
        wpx  = page["width_px"];  hpx = page["height_px"]
        dpi  = page["dpi"]
        wpt  = wpx * 72 / dpi;   hpt = hpx * 72 / dpi
        cols = page["text_columns"]
        imgs = page["image_regions"]
        print(f"\n{'='*60}")
        print(f"第 {pn} 页   {wpx}×{hpx}px  ({wpt:.0f}×{hpt:.0f}pt)  "
              f"dpi={dpi}   列数={len(cols)}  图片={len(imgs)}")
        print(f"{'─'*60}")
        for col in cols:
            x1,y1,x2,y2 = col["col_bbox"]
            cx = (x1+x2)/2; cy = (y1+y2)/2
            n  = len(col["chars"])
            cxpt = cx*72/dpi; x1pt=x1*72/dpi; x2pt=x2*72/dpi
            y1pt = y1*72/dpi; y2pt=y2*72/dpi
            preview = "".join(c["text"] for c in col["chars"][:8] if c["text"].strip())
            print(f"  列{col['source_order']:2d} │ "
                  f"bbox_px=({x1:4d},{y1:4d},{x2:4d},{y2:4d})  "
                  f"cx={cxpt:6.1f}pt  "
                  f"y={y1pt:.0f}~{y2pt:.0f}pt  "
                  f"字数={n:3d}  「{preview}…」")
        if imgs:
            for img in imgs:
                x1,y1,x2,y2 = img["bbox"]
                print(f"  [图] bbox_px=({x1},{y1},{x2},{y2})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf",    default="E:/zywc.pdf")
    parser.add_argument("--pages",  default="1-20")
    parser.add_argument("--dpi",    type=int, default=300)
    parser.add_argument("--out",    default=None,
                        help="输出 JSON 路径（默认自动生成）")
    parser.add_argument("--inspect",action="store_true",
                        help="只打印已有缓存，不重跑 OCR")
    args = parser.parse_args()

    m = re.fullmatch(r"(\d+)-(\d+)", args.pages.strip())
    if not m: raise ValueError(f"pages 格式错误: {args.pages}")
    p_start, p_end = int(m.group(1)), int(m.group(2))

    stem = os.path.splitext(os.path.basename(args.pdf))[0]
    cache_path = args.out or f"output/ocr_cache_{stem}_p{p_start}-{p_end}.json"
    os.makedirs("output", exist_ok=True)

    if args.inspect:
        if not os.path.exists(cache_path):
            print(f"缓存不存在: {cache_path}")
            return
        data = json.loads(open(cache_path, encoding="utf-8").read())
        inspect_cache(data)
        return

    if os.path.exists(cache_path):
        print(f"缓存已存在，跳过 OCR: {cache_path}")
        data = json.loads(open(cache_path, encoding="utf-8").read())
    else:
        data = run_ocr(args.pdf, p_start, p_end, args.dpi)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已保存缓存: {cache_path}")

    inspect_cache(data)


if __name__ == "__main__":
    main()
