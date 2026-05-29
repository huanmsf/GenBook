"""tests/test_pdf_reader.py"""
import io
import os
import pytest
import fitz  # PyMuPDF
from modules.pdf_reader import pdf_to_images, PageImage


def _make_single_page_pdf(tmp_path) -> str:
    """Helper: create a minimal 1-page PDF file for testing."""
    pdf_path = str(tmp_path / "sample.pdf")
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 in points
    page.insert_text((50, 100), "測試文字", fontsize=20)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def test_pdf_to_images_raises_on_missing_file():
    with pytest.raises(Exception):
        pdf_to_images("nonexistent_file.pdf")


def test_pdf_to_images_returns_list_of_page_images(tmp_path):
    pdf_path = _make_single_page_pdf(tmp_path)
    result = pdf_to_images(pdf_path, dpi=72)
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], PageImage)


def test_page_image_has_correct_page_num(tmp_path):
    pdf_path = _make_single_page_pdf(tmp_path)
    result = pdf_to_images(pdf_path, dpi=72)
    assert result[0].page_num == 1


def test_page_image_has_correct_dpi(tmp_path):
    pdf_path = _make_single_page_pdf(tmp_path)
    result = pdf_to_images(pdf_path, dpi=150)
    assert result[0].dpi == 150


def test_page_image_bytes_are_valid_png(tmp_path):
    pdf_path = _make_single_page_pdf(tmp_path)
    result = pdf_to_images(pdf_path, dpi=72)
    img_bytes = result[0].image_bytes
    # PNG magic bytes: \x89PNG
    assert img_bytes[:4] == b"\x89PNG"


def test_page_image_dimensions_scale_with_dpi(tmp_path):
    pdf_path = _make_single_page_pdf(tmp_path)
    low = pdf_to_images(pdf_path, dpi=72)[0]
    high = pdf_to_images(pdf_path, dpi=144)[0]
    assert high.orig_width_px > low.orig_width_px
    assert high.orig_height_px > low.orig_height_px



def _make_multi_page_pdf(tmp_path, n=5):
    pdf_path = str(tmp_path / 'multi.pdf')
    doc = fitz.open()
    for i in range(n):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 100), f'Page {i+1}', fontsize=20)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def test_page_range_returns_subset(tmp_path):
    pdf_path = _make_multi_page_pdf(tmp_path, n=5)
    result = pdf_to_images(pdf_path, dpi=72, page_start=2, page_end=4)
    assert len(result) == 3
    assert result[0].page_num == 2
    assert result[-1].page_num == 4


def test_page_range_default_all_pages(tmp_path):
    pdf_path = _make_multi_page_pdf(tmp_path, n=3)
    result = pdf_to_images(pdf_path, dpi=72)
    assert len(result) == 3


def test_page_range_start_only(tmp_path):
    pdf_path = _make_multi_page_pdf(tmp_path, n=5)
    result = pdf_to_images(pdf_path, dpi=72, page_start=3)
    assert len(result) == 3
    assert result[0].page_num == 3
