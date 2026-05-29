"""公共测试 fixtures。"""
import pytest
import io
from PIL import Image


@pytest.fixture
def sample_white_page_bytes() -> bytes:
    """生成一张 200x300 白色图片（用于测试）。"""
    img = Image.new("RGB", (200, 300), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
