"""tests/test_ocr_engine.py"""
import os
import pytest
from unittest.mock import patch, MagicMock
from modules.ocr_engine import CharResult, sort_vertical_chars, recognize_region, load_env


# ---------------------------------------------------------------------------
# sort_vertical_chars 单元测试（不依赖任何外部服务）
# ---------------------------------------------------------------------------

def test_sort_vertical_chars_right_to_left():
    """列应按 X 坐标从右到左排序（竖排：右边列优先）。"""
    chars = [
        CharResult(text="A", bbox=(10, 0, 30, 20), confidence=1.0),   # 左列
        CharResult(text="B", bbox=(100, 0, 120, 20), confidence=1.0), # 右列
    ]
    sorted_chars = sort_vertical_chars(chars)
    assert sorted_chars[0].text == "B"
    assert sorted_chars[1].text == "A"


def test_sort_vertical_chars_top_to_bottom_within_column():
    """同列内字符按 Y 坐标从上到下排序。"""
    chars = [
        CharResult(text="下", bbox=(50, 80, 70, 100), confidence=1.0),
        CharResult(text="上", bbox=(50, 10, 70, 30),  confidence=1.0),
    ]
    sorted_chars = sort_vertical_chars(chars)
    assert sorted_chars[0].text == "上"
    assert sorted_chars[1].text == "下"


def test_sort_vertical_chars_multi_column_order():
    """两列各两字，结果应为：右列上->下, 左列上->下。"""
    chars = [
        CharResult(text="左上", bbox=(10, 10, 30, 30),  confidence=1.0),
        CharResult(text="左下", bbox=(10, 50, 30, 70),  confidence=1.0),
        CharResult(text="右上", bbox=(100, 10, 120, 30), confidence=1.0),
        CharResult(text="右下", bbox=(100, 50, 120, 70), confidence=1.0),
    ]
    sorted_chars = sort_vertical_chars(chars)
    texts = [c.text for c in sorted_chars]
    assert texts == ["右上", "右下", "左上", "左下"]


def test_sort_vertical_chars_empty_list():
    assert sort_vertical_chars([]) == []


# ---------------------------------------------------------------------------
# recognize_region：mock Google Vision API
# ---------------------------------------------------------------------------

def _make_mock_vision_response(char_texts: list[str]):
    """构造一个仿 Google Vision API 返回的 mock 对象。"""
    mock_resp = MagicMock()
    symbols = []
    for i, ch in enumerate(char_texts):
        sym = MagicMock()
        sym.text = ch
        sym.confidence = 0.99
        # bounding box: 4 vertices
        verts = [MagicMock() for _ in range(4)]
        verts[0].x, verts[0].y = i * 20, 0
        verts[1].x, verts[1].y = i * 20 + 18, 0
        verts[2].x, verts[2].y = i * 20 + 18, 20
        verts[3].x, verts[3].y = i * 20, 20
        sym.bounding_box.vertices = verts
        symbols.append(sym)

    word = MagicMock()
    word.symbols = symbols
    para = MagicMock()
    para.words = [word]
    block = MagicMock()
    block.paragraphs = [para]
    page = MagicMock()
    page.blocks = [block]
    mock_resp.full_text_annotation.pages = [page]
    return mock_resp


def test_recognize_region_returns_char_results(sample_white_page_bytes, monkeypatch):
    """强制使用 google 后端（mock），验证 recognize_region 返回 CharResult 列表。"""
    monkeypatch.setenv("OCR_BACKEND", "google")
    mock_client = MagicMock()
    mock_client.document_text_detection.return_value = _make_mock_vision_response(["書", "法"])
    with patch("modules.ocr_engine._get_vision_client", return_value=mock_client):
        results = recognize_region(sample_white_page_bytes, region_bbox=(0, 0, 200, 300))
    assert len(results) == 2
    assert all(isinstance(r, CharResult) for r in results)


def test_recognize_region_filters_low_confidence(sample_white_page_bytes, monkeypatch):
    """强制使用 google 后端（mock），验证低置信度字符被过滤。"""
    monkeypatch.setenv("OCR_BACKEND", "google")
    mock_client = MagicMock()
    resp = _make_mock_vision_response(["書"])
    resp.full_text_annotation.pages[0].blocks[0].paragraphs[0].words[0].symbols[0].confidence = 0.3
    mock_client.document_text_detection.return_value = resp
    with patch("modules.ocr_engine._get_vision_client", return_value=mock_client):
        results = recognize_region(
            sample_white_page_bytes,
            region_bbox=(0, 0, 200, 300),
            confidence_threshold=0.7,
        )
    assert results == []


def test_recognize_region_unknown_backend_raises(sample_white_page_bytes, monkeypatch):
    """不支持的后端名称应抛出 ValueError。"""
    monkeypatch.setenv("OCR_BACKEND", "unknown_backend")
    with pytest.raises(ValueError, match="不支持的 OCR_BACKEND"):
        recognize_region(sample_white_page_bytes, region_bbox=(0, 0, 200, 300))

# load_env tests

def test_load_env_reads_env_file(tmp_path):
    import os as _os
    env_file = tmp_path / '.env'
    env_file.write_text('BAIDU_OCR_APP_ID=test_id\nOCR_BACKEND=baidu\n', encoding='utf-8')
    _os.environ.pop('BAIDU_OCR_APP_ID', None)
    load_env(str(env_file))
    assert _os.environ.get('BAIDU_OCR_APP_ID') == 'test_id'

def test_load_env_missing_file_does_not_raise(tmp_path):
    load_env(str(tmp_path / 'nonexistent.env'))

def test_load_env_default_path_does_not_raise():
    load_env()
