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


def test_text_column_default_metadata():
    col = TextColumn(bbox=(10, 20, 30, 40))
    assert col.column_type == "main"
    assert col.source_order == 0
    assert col.slot_index == 0
    assert col.expected_char_count == 0


def test_text_column_expected_char_count_auto_filled():
    col = TextColumn(
        bbox=(10, 20, 30, 40),
        chars=[
            CharData(text="周", bbox=(1, 1, 2, 2), confidence=1.0),
            CharData(text="易", bbox=(1, 2, 2, 3), confidence=1.0),
        ],
    )
    assert col.expected_char_count == 2


def test_text_column_manual_expected_char_count_preserved():
    col = TextColumn(
        bbox=(10, 20, 30, 40),
        chars=[CharData(text="周", bbox=(1, 1, 2, 2), confidence=1.0)],
        column_type="title",
        source_order=3,
        slot_index=5,
        expected_char_count=8,
    )
    assert col.column_type == "title"
    assert col.source_order == 3
    assert col.slot_index == 5
    assert col.expected_char_count == 8
