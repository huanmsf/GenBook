"""tests/test_img_pipeline.py — 图片入口与横排 writer（不改原模块）。"""
from __future__ import annotations
import os
from PIL import Image

from img import resolve_layout, resolve_flow, parse_args
from modules.image_reader import collect_image_paths, images_to_pages, is_image_file
from modules.pdf_writer import load_config
from modules.typst_horizontal_writer import (
    create_typst,
    _build_header,
    _union_word_items,
    _cluster_rows,
)
from modules.page_model import PageData, TextColumn, CharData


def test_is_image_file():
    assert is_image_file("a.PNG")
    assert is_image_file("b.jpg")
    assert not is_image_file("c.pdf")


def test_collect_and_pages(tmp_path):
    img = Image.new("RGB", (80, 120), (255, 255, 255))
    p1 = tmp_path / "p1.png"
    p2 = tmp_path / "p2.jpg"
    img.save(p1)
    img.save(p2)
    paths = collect_image_paths([str(tmp_path)])
    assert len(paths) == 2
    pages = images_to_pages(paths, dpi=300, page_start=1, page_end=1)
    assert len(pages) == 1
    assert pages[0].page_num == 1
    assert pages[0].orig_width_px == 80
    assert pages[0].orig_height_px == 120


def test_resolve_layout_auto_from_cn_config():
    cfg = load_config("config/layout_config_modern_cn.yaml")
    assert resolve_layout("auto", cfg) == "horizontal"
    tw = load_config("config/layout_config_modern_tw.yaml")
    assert resolve_layout("auto", tw) == "vertical"
    assert resolve_layout("horizontal", tw) == "horizontal"


def test_img_cli_parse():
    ns = parse_args(["foo.png", "--layout", "vertical"])
    assert ns.layout == "vertical"
    assert ns.inputs == ["foo.png"]
    assert ns.flow is None
    assert parse_args(["foo.png", "--flow"]).flow is True
    assert parse_args(["foo.png", "--no-flow"]).flow is False


def test_resolve_flow_defaults():
    assert resolve_flow(None, "horizontal") is False
    assert resolve_flow(None, "vertical") is True
    assert resolve_flow(True, "horizontal") is True
    assert resolve_flow(False, "vertical") is False


def _horizontal_page() -> PageData:
    line1 = "天尊地卑乾坤定矣"
    line2 = "卑高以陈贵贱位矣"
    chars = []
    for i, ch in enumerate(line1):
        chars.append(CharData(
            text=ch, bbox=(100 + i * 40, 120, 136 + i * 40, 168), confidence=0.99,
        ))
    for i, ch in enumerate(line2):
        chars.append(CharData(
            text=ch, bbox=(100 + i * 40, 200, 136 + i * 40, 248), confidence=0.99,
        ))
    return PageData(
        page_num=1, orig_width_px=2480, orig_height_px=3508, dpi=300,
        text_columns=[TextColumn(bbox=(100, 120, 900, 250), chars=chars)],
        image_regions=[],
    )


def test_horizontal_writer_from_cache_like_page(tmp_path):
    page = _horizontal_page()
    cfg = load_config("config/layout_config_modern_cn.yaml")
    header = _build_header(cfg)
    assert "横排绝对坐标" in header
    assert "width: 140mm" in header
    assert 'region: "CN"' in header
    assert "#let hrow" in header
    assert "#let vcol" not in header

    typ_path = str(tmp_path / "out.typ")
    create_typst([page], typ_path, cfg)
    content = open(typ_path, encoding="utf-8").read()
    assert "天尊地卑乾坤定矣" in content
    assert "#place(top + left" in content
    assert "#hrow(" in content
    assert "#par[" not in content
    assert "#grid(" not in content
    assert os.path.exists(typ_path)


def test_union_vertical_slices_become_ltr_row():
    """百度竖切词（同 x 竖条）应还原为同一高度、从左到右。"""
    slices = [
        CharData(text=ch, bbox=(964, 19 + i * 6, 1056, 25 + i * 6), confidence=0.99)
        for i, ch in enumerate("23:55")
    ]
    items = _union_word_items(slices)
    assert len(items) == 1
    assert items[0]["text"] == "23:55"
    assert items[0]["y1"] == 19
    xs = [c.bbox[0] for c in items[0]["chars"]]
    assert xs == sorted(xs)
    assert items[0]["chars"][0].text == "2"
    assert items[0]["chars"][-1].text == "5"


def test_cluster_rows_same_height_ltr():
    items = [
        {"text": "右", "x1": 800, "y1": 100, "x2": 840, "y2": 140, "chars": []},
        {"text": "左", "x1": 40, "y1": 102, "x2": 80, "y2": 142, "chars": []},
        {"text": "次行", "x1": 40, "y1": 200, "x2": 120, "y2": 240, "chars": []},
    ]
    rows = _cluster_rows(items)
    assert len(rows) == 2
    assert [it["text"] for it in rows[0]] == ["左", "右"]
    assert [it["text"] for it in rows[1]] == ["次行"]


def test_horizontal_abs_places_rows_by_json_coords(tmp_path):
    page = _horizontal_page()
    cfg = load_config("config/layout_config_modern_cn.yaml")
    typ_path = str(tmp_path / "out.typ")
    create_typst([page], typ_path, cfg)
    content = open(typ_path, encoding="utf-8").read()
    assert "天尊地卑乾坤定矣" in content
    assert "卑高以陈贵贱位矣" in content
    import re
    places = re.findall(
        r"#place\(top \+ left, dx: ([0-9.]+)pt, dy: ([0-9.]+)pt\)\[#hrow\(\"([^\"]*)\"\)\]",
        content,
    )
    assert places
    dys = [float(p[1]) for p in places]
    assert min(dys) < max(dys)
    line1 = [p for p in places if float(p[1]) == min(dys)]
    line2 = [p for p in places if float(p[1]) == max(dys)]
    assert "".join(p[2] for p in line1) == "天尊地卑乾坤定矣"
    assert "".join(p[2] for p in line2) == "卑高以陈贵贱位矣"


def test_same_row_keeps_separate_x_from_json(tmp_path):
    chars = [
        CharData(text="甲", bbox=(40, 80, 80, 120), confidence=0.99),
        CharData(text="乙", bbox=(900, 82, 940, 122), confidence=0.99),
    ]
    page = PageData(
        page_num=1, orig_width_px=1000, orig_height_px=400, dpi=300,
        text_columns=[TextColumn(bbox=(40, 80, 940, 122), chars=chars)],
        image_regions=[],
    )
    cfg = load_config("config/layout_config_modern_cn.yaml")
    typ_path = str(tmp_path / "split_x.typ")
    create_typst([page], typ_path, cfg)
    content = open(typ_path, encoding="utf-8").read()
    import re
    places = re.findall(
        r"#place\(top \+ left, dx: ([0-9.]+)pt, dy: ([0-9.]+)pt\)\[#hrow\(\"([^\"]*)\"\)\]",
        content,
    )
    assert len(places) == 2
    assert places[0][2] == "甲" and places[1][2] == "乙"
    assert float(places[0][1]) == float(places[1][1])
    assert float(places[0][0]) < float(places[1][0])


def test_horizontal_writer_flow_mode(tmp_path):
    page = _horizontal_page()
    cfg = load_config("config/layout_config_modern_cn.yaml")
    typ_path = str(tmp_path / "out_flow.typ")
    create_typst([page], typ_path, cfg, flow=True)
    content = open(typ_path, encoding="utf-8").read()
    assert "#par" in content
    assert "横排流式段落" in content
    assert "#let hrow" not in content
