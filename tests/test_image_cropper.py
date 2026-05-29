"""tests/test_image_cropper.py"""
import io
import pytest
from PIL import Image
from modules.image_cropper import crop_image_region, CroppedImage


def test_crop_returns_cropped_image_instance(sample_white_page_bytes):
    bbox = (10, 10, 100, 100)
    result = crop_image_region(sample_white_page_bytes, bbox, page_num=1)
    assert isinstance(result, CroppedImage)


def test_crop_image_bytes_are_valid_png(sample_white_page_bytes):
    bbox = (0, 0, 50, 50)
    result = crop_image_region(sample_white_page_bytes, bbox, page_num=1)
    assert result.image_bytes[:4] == b"\x89PNG"


def test_crop_preserves_bbox(sample_white_page_bytes):
    bbox = (10, 20, 80, 90)
    result = crop_image_region(sample_white_page_bytes, bbox, page_num=2)
    assert result.bbox == bbox
    assert result.page_num == 2


def test_crop_output_size_matches_bbox(sample_white_page_bytes):
    bbox = (10, 10, 60, 80)  # width=50, height=70
    result = crop_image_region(sample_white_page_bytes, bbox, page_num=1)
    img = Image.open(io.BytesIO(result.image_bytes))
    assert img.size == (50, 70)


def test_crop_raises_on_out_of_bounds(sample_white_page_bytes):
    with pytest.raises(ValueError):
        crop_image_region(sample_white_page_bytes, (0, 0, 9999, 9999), page_num=1)
