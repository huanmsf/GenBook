"""tests/test_ocr_engine.py"""
import os
import pytest
from unittest.mock import patch, MagicMock
from modules.ocr_engine import (
    CharResult, sort_vertical_chars, recognize_region, load_env,
    paddle_vl_pages_to_chars, enable_paddle_vl, _baidu_word_to_chars,
)


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


def test_paddle_vl_pages_to_chars_layout_and_span():
    pages = [{
        "layouts": [
            {
                "type": "text",
                "text": "天地",
                "position": [10, 20, 40, 16],
            },
            {
                "type": "vertical_text",
                "text": "",
                "position": [100, 10, 18, 40],
                "span_boxes": [
                    {"text": "乾", "location": [100, 10, 18, 20]},
                    {"text": "坤", "location": [100, 30, 18, 20]},
                ],
            },
            {
                "type": "image",
                "text": "ignore",
                "position": [0, 0, 10, 10],
            },
        ],
    }]
    chars = paddle_vl_pages_to_chars(pages, ox=5, oy=7, confidence_threshold=0.7)
    texts = [c.text for c in chars]
    assert texts == ["天", "地", "乾", "坤"]
    assert chars[0].bbox[0] == 15  # 10 + ox


def test_paddle_vl_polygon_box():
    pages = [{
        "layouts": [{
            "type": "text",
            "text": "甲",
            "position": [[10, 20], [30, 20], [30, 40], [10, 40]],
        }],
    }]
    chars = paddle_vl_pages_to_chars(pages, ox=0, oy=0, confidence_threshold=0.7)
    assert chars[0].text == "甲"
    assert chars[0].bbox == (10, 20, 30, 40)


def test_baidu_word_uses_char_boxes():
    word = {
        "words": "乾坤",
        "probability": {"average": 0.99},
        "location": {"left": 10, "top": 20, "width": 20, "height": 80},
        "chars": [
            {"char": "乾", "location": {"left": 10, "top": 20, "width": 20, "height": 40}},
            {"char": "坤", "location": {"left": 10, "top": 60, "width": 20, "height": 40}},
        ],
    }
    chars = _baidu_word_to_chars(word, ox=5, oy=7, confidence_threshold=0.7)
    assert [c.text for c in chars] == ["乾", "坤"]
    assert chars[0].bbox == (15, 27, 35, 67)
    assert chars[1].bbox == (15, 67, 35, 107)


def test_baidu_word_fallback_horizontal_split():
    word = {
        "words": "甲乙",
        "probability": {"average": 0.9},
        "location": {"left": 0, "top": 0, "width": 40, "height": 10},
    }
    chars = _baidu_word_to_chars(word, ox=0, oy=0, confidence_threshold=0.7)
    assert [c.text for c in chars] == ["甲", "乙"]
    assert chars[0].bbox[0] < chars[1].bbox[0]
    assert chars[0].bbox[1] == chars[1].bbox[1]


def test_baidu_accurate_requests_small_granularity(monkeypatch, sample_white_page_bytes):
    mock_client = MagicMock()
    mock_client.accurate.return_value = {"words_result": []}
    monkeypatch.setenv("OCR_BACKEND", "baidu")
    monkeypatch.delenv("BAIDU_OCR_API", raising=False)
    with patch("modules.ocr_engine._get_baidu_client", return_value=mock_client):
        recognize_region(sample_white_page_bytes, (0, 0, 10, 10))
    opts = mock_client.accurate.call_args[0][1]
    assert opts["recognize_granularity"] == "small"
    assert opts["probability"] == "true"


def test_baidu_accurate_logs_error_and_returns_empty(monkeypatch, sample_white_page_bytes, caplog):
    mock_client = MagicMock()
    mock_client.accurate.return_value = {
        "error_code": 216205,
        "error_msg": "input oversize",
    }
    monkeypatch.setenv("OCR_BACKEND", "baidu")
    monkeypatch.delenv("BAIDU_OCR_API", raising=False)
    with patch("modules.ocr_engine._get_baidu_client", return_value=mock_client):
        with caplog.at_level("WARNING"):
            out = recognize_region(sample_white_page_bytes, (0, 0, 10, 10))
    assert out == []
    assert "216205" in caplog.text or "oversize" in caplog.text


def test_enable_paddle_vl_routes_recognize(monkeypatch, sample_white_page_bytes):
    enable_paddle_vl(True)
    monkeypatch.setenv("OCR_BACKEND", "baidu")
    try:
        with patch(
            "modules.ocr_engine._recognize_baidu_paddle_vl",
            return_value=[CharResult("甲", (0, 0, 8, 8), 0.99)],
        ) as mocked:
            out = recognize_region(sample_white_page_bytes, (0, 0, 10, 10))
        mocked.assert_called_once()
        assert out[0].text == "甲"
    finally:
        enable_paddle_vl(False)
