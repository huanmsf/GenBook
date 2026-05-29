"""tests/test_layout_analyzer.py"""
import pytest
from unittest.mock import patch, MagicMock
from modules.layout_analyzer import Region, analyze_layout, _ppstructure_to_regions


def test_region_dataclass_fields():
    r = Region(region_type="text", bbox=(0, 0, 100, 200))
    assert r.region_type == "text"
    assert r.bbox == (0, 0, 100, 200)


def test_ppstructure_to_regions_text_type():
    """PPStructure 返回 type=text 的块应转为 Region(text)。"""
    raw = [{"type": "text", "bbox": [10, 20, 110, 220]}]
    regions = _ppstructure_to_regions(raw)
    assert len(regions) == 1
    assert regions[0].region_type == "text"
    assert regions[0].bbox == (10, 20, 110, 220)


def test_ppstructure_to_regions_figure_type():
    """PPStructure 返回 type=figure 的块应转为 Region(image)。"""
    raw = [{"type": "figure", "bbox": [50, 50, 200, 300]}]
    regions = _ppstructure_to_regions(raw)
    assert regions[0].region_type == "image"


def test_ppstructure_to_regions_filters_tiny_regions():
    """面积过小的区域（噪点）应被过滤。"""
    raw = [{"type": "text", "bbox": [0, 0, 5, 5]}]   # 25px², 噪点
    regions = _ppstructure_to_regions(raw)
    assert regions == []


def test_ppstructure_to_regions_mixed():
    raw = [
        {"type": "text",   "bbox": [0,   0,  100, 200]},
        {"type": "figure", "bbox": [200, 0,  400, 300]},
        {"type": "text",   "bbox": [0,   0,    3,   3]},  # tiny, filtered
    ]
    regions = _ppstructure_to_regions(raw)
    assert len(regions) == 2


def test_analyze_layout_returns_list(sample_white_page_bytes):
    """analyze_layout 对空白图片应返回空列表（mock PPStructure）。"""
    with patch("modules.layout_analyzer._run_ppstructure", return_value=[]):
        result = analyze_layout(sample_white_page_bytes)
    assert isinstance(result, list)


def test_analyze_layout_returns_regions_from_ppstructure(sample_white_page_bytes):
    mock_result = [
        {"type": "text",   "bbox": [0,   0, 200, 300]},
        {"type": "figure", "bbox": [50, 50, 150, 200]},
    ]
    with patch("modules.layout_analyzer._run_ppstructure", return_value=mock_result):
        result = analyze_layout(sample_white_page_bytes)
    assert len(result) == 2
    types = {r.region_type for r in result}
    assert types == {"text", "image"}
