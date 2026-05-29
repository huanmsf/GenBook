"""tests/test_pdf_writer.py"""
import io
import os
import pytest
import fitz
from modules.page_model import PageData, TextColumn, ImageRegion, CharData
from modules.pdf_writer import load_config, create_pdf


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

def test_load_config_returns_dict(tmp_path):
    cfg_file = tmp_path / "test_config.yaml"
    cfg_file.write_text("font_size: 16\nline_spacing: 2.0\n", encoding="utf-8")
    cfg = load_config(str(cfg_file))
    assert isinstance(cfg, dict)
    assert cfg["font_size"] == 16


def test_load_config_default_path_exists():
    """默认 config/layout_config.yaml 应存在且可加载。"""
    cfg = load_config("config/layout_config.yaml")
    assert "font_size" in cfg
    assert "font_path" in cfg


# ---------------------------------------------------------------------------
# create_pdf
# ---------------------------------------------------------------------------

def _make_simple_page() -> PageData:
    col = TextColumn(
        bbox=(0, 0, 50, 200),
        chars=[
            CharData(text="書", bbox=(5, 5, 45, 45), confidence=0.99),
            CharData(text="法", bbox=(5, 50, 45, 90), confidence=0.99),
        ],
    )
    return PageData(
        page_num=1,
        orig_width_px=595,
        orig_height_px=842,
        dpi=72,
        text_columns=[col],
        image_regions=[],
    )


def test_create_pdf_produces_file(tmp_path):
    output = str(tmp_path / "out.pdf")
    cfg = load_config("config/layout_config.yaml")
    create_pdf([_make_simple_page()], output, cfg)
    assert os.path.exists(output)
    assert os.path.getsize(output) > 0


def test_create_pdf_is_valid_pdf(tmp_path):
    output = str(tmp_path / "out.pdf")
    cfg = load_config("config/layout_config.yaml")
    create_pdf([_make_simple_page()], output, cfg)
    doc = fitz.open(output)
    assert len(doc) == 1
    doc.close()


def test_create_pdf_text_is_searchable(tmp_path):
    """PDF 文字层应可提取（字体不存在时 CJK 降级为替代字符，但文字层存在）。"""
    output = str(tmp_path / "out.pdf")
    cfg = load_config("config/layout_config.yaml")
    create_pdf([_make_simple_page()], output, cfg)
    doc = fitz.open(output)
    page = doc[0]
    text = page.get_text()
    # 有 CJK 字体时包含原文；无字体时降级字符也应为非空字符串
    assert len(text.strip()) > 0
    doc.close()


def test_create_pdf_with_image_region(tmp_path):
    """含图片区域时不应报错，且生成有效 PDF。"""
    import io as _io
    from PIL import Image as _Image
    img = _Image.new("RGB", (100, 100), color=(200, 100, 50))
    buf = _io.BytesIO()
    img.save(buf, format="PNG")

    page = PageData(
        page_num=1,
        orig_width_px=595,
        orig_height_px=842,
        dpi=72,
        text_columns=[],
        image_regions=[ImageRegion(bbox=(100, 100, 200, 200), image_bytes=buf.getvalue())],
    )
    output = str(tmp_path / "img_out.pdf")
    cfg = load_config("config/layout_config.yaml")
    create_pdf([page], output, cfg)
    doc = fitz.open(output)
    assert len(doc) == 1
    doc.close()
