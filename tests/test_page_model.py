"""tests/test_page_model.py"""
import pytest
from modules.page_model import PageData, TextColumn, ImageRegion, CharData


def test_page_data_default_empty_columns():
    page = PageData(page_num=1, orig_width_px=800, orig_height_px=1200, dpi=300)
    assert page.text_columns == []
    assert page.image_regions == []


def test_char_data_fields():
    c = CharData(text="書", bbox=(10, 20, 30, 40), confidence=0.95)
    assert c.text == "書"
    assert c.confidence == 0.95
