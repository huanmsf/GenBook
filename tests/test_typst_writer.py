"""tests/test_typst_writer.py — typst_writer 单元测试"""
from __future__ import annotations
import os
import tempfile
import pytest

from modules.page_model import PageData, TextColumn, CharData, ImageRegion
from modules.typst_writer import (
    build_typ_output_path,
    _escape_typst,
    _px_to_pt,
    create_typst,
)

# ---------------------------------------------------------------------------
# 辅助：最小 PageData
# ---------------------------------------------------------------------------

def _make_page(page_num=1, w=2480, h=3508, dpi=300) -> PageData:
    col = TextColumn(
        bbox=(100, 100, 200, 900),
        chars=[
            CharData(text="天", bbox=(100, 100, 200, 200), confidence=0.99),
            CharData(text="地", bbox=(100, 200, 200, 300), confidence=0.95),
            CharData(text="玄", bbox=(100, 300, 200, 400), confidence=0.90),
        ],
    )
    return PageData(
        page_num=page_num,
        orig_width_px=w,
        orig_height_px=h,
        dpi=dpi,
        text_columns=[col],
        image_regions=[],
    )


def _make_page_with_image(page_num=1) -> PageData:
    img_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100   # fake PNG
    page = _make_page(page_num=page_num)
    page.image_regions = [
        ImageRegion(bbox=(300, 400, 700, 900), image_bytes=img_bytes)
    ]
    return page


# ---------------------------------------------------------------------------
# build_typ_output_path
# ---------------------------------------------------------------------------

class TestBuildTypOutputPath:
    def test_replaces_pdf_extension(self):
        path = build_typ_output_path("output/book_out_20260101.pdf")
        assert path.endswith(".typ")
        assert path == "output/book_out_20260101.typ"

    def test_stem_preserved(self):
        path = build_typ_output_path("output/zywc_out_123.pdf")
        assert "zywc_out_123" in path

    def test_non_pdf_extension_gets_typ(self):
        path = build_typ_output_path("output/result")
        assert path.endswith(".typ")


# ---------------------------------------------------------------------------
# _escape_typst
# ---------------------------------------------------------------------------

class TestEscapeTypst:
    def test_escapes_hash(self):
        assert r"\#" in _escape_typst("第#一章")

    def test_escapes_at(self):
        assert r"\@" in _escape_typst("mail@test")

    def test_escapes_backslash(self):
        result = _escape_typst("a\\b")
        assert "\\\\" in result

    def test_normal_cjk_unchanged(self):
        text = "天地玄黃宇宙洪荒"
        assert _escape_typst(text) == text

    def test_empty_string(self):
        assert _escape_typst("") == ""


# ---------------------------------------------------------------------------
# _px_to_pt
# ---------------------------------------------------------------------------

class TestPxToPt:
    def test_300dpi(self):
        assert abs(_px_to_pt(300, 300) - 72.0) < 0.01

    def test_72dpi(self):
        assert abs(_px_to_pt(72, 72) - 72.0) < 0.01

    def test_zero(self):
        assert _px_to_pt(0, 300) == 0.0


# ---------------------------------------------------------------------------
# create_typst  — 集成测试（不依赖网络/字体）
# ---------------------------------------------------------------------------

class TestCreateTypst:
    def _default_config(self):
        return {
            "font_family": "STKaiTi",
            "font_path":   "fonts/STKAITI.TTF",
            "font_size":   14,
            "line_spacing": 1.8,
            "column_spacing": 10,
            "page_margin": {"top": 36, "bottom": 36, "left": 36, "right": 36},
            "page_size":   "original",
        }

    def test_creates_typ_file(self, tmp_path):
        pages = [_make_page()]
        typ_path = str(tmp_path / "out.typ")
        create_typst(pages, typ_path, self._default_config())
        assert os.path.exists(typ_path)

    def test_typ_file_contains_cjk_text(self, tmp_path):
        pages = [_make_page()]
        typ_path = str(tmp_path / "out.typ")
        create_typst(pages, typ_path, self._default_config())
        content = open(typ_path, encoding="utf-8").read()
        assert "天" in content
        assert "地" in content
        assert "玄" in content

    def test_typ_file_has_page_header(self, tmp_path):
        pages = [_make_page(page_num=3)]
        typ_path = str(tmp_path / "out.typ")
        create_typst(pages, typ_path, self._default_config())
        content = open(typ_path, encoding="utf-8").read()
        # 每页有注释标记
        assert "page 3" in content.lower() or "第 3 页" in content

    def test_typ_file_font_set(self, tmp_path):
        pages = [_make_page()]
        typ_path = str(tmp_path / "out.typ")
        create_typst(pages, typ_path, self._default_config())
        content = open(typ_path, encoding="utf-8").read()
        assert "STKaiTi" in content

    def test_image_region_exports_asset(self, tmp_path):
        pages = [_make_page_with_image()]
        typ_path = str(tmp_path / "out.typ")
        create_typst(pages, typ_path, self._default_config())
        # assets 子目录应存在图片文件
        assets_dir = tmp_path / "assets"
        assert assets_dir.exists()
        imgs = list(assets_dir.iterdir())
        assert len(imgs) == 1

    def test_image_region_referenced_in_typ(self, tmp_path):
        pages = [_make_page_with_image()]
        typ_path = str(tmp_path / "out.typ")
        create_typst(pages, typ_path, self._default_config())
        content = open(typ_path, encoding="utf-8").read()
        assert "image(" in content

    def test_multiple_pages(self, tmp_path):
        pages = [_make_page(page_num=i) for i in range(1, 4)]
        typ_path = str(tmp_path / "out.typ")
        create_typst(pages, typ_path, self._default_config())
        content = open(typ_path, encoding="utf-8").read()
        # pagebreak 应出现在多页输出中
        assert "pagebreak" in content

    def test_empty_pages_creates_file(self, tmp_path):
        typ_path = str(tmp_path / "out.typ")
        create_typst([], typ_path, self._default_config())
        assert os.path.exists(typ_path)

