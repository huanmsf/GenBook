"""OCR 模块：支持多云端 OCR 后端（百度/腾讯/阿里/Google）。

通过环境变量 OCR_BACKEND 切换后端（默认 baidu）：
    set OCR_BACKEND=baidu    # 百度智能云（推荐，国内首选）
    set OCR_BACKEND=tencent  # 腾讯云
    set OCR_BACKEND=google   # Google Cloud Vision（需科学上网）

各后端所需环境变量：
    百度:   BAIDU_OCR_APP_ID, BAIDU_OCR_API_KEY, BAIDU_OCR_SECRET_KEY
    腾讯:   TENCENT_SECRET_ID, TENCENT_SECRET_KEY, TENCENT_REGION(可选)
    Google: GOOGLE_APPLICATION_CREDENTIALS
"""
from __future__ import annotations
import base64
import io
import os
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# .env 加载（模块导入时自动执行）
# ---------------------------------------------------------------------------

def load_env(env_path: str | None = None) -> None:
    """从 .env 文件加载配置到 os.environ。

    Args:
        env_path: .env 文件路径。默认为项目根目录的 .env。
                  文件不存在时静默忽略（不抛出异常）。
    """
    if env_path is None:
        # 默认路径：本文件所在目录的上一级（项目根目录）
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")

    env_path = os.path.abspath(env_path)
    if not os.path.exists(env_path):
        return  # 文件不存在时静默忽略

    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)  # override=False: 已有环境变量优先
    except ImportError:
        # python-dotenv 未安装时，手动解析
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value


# 模块导入时自动加载项目根目录的 .env
load_env()


# ---------------------------------------------------------------------------
# 数据模型（所有后端共用）
# ---------------------------------------------------------------------------

@dataclass
class CharResult:
    text: str
    bbox: tuple[int, int, int, int]   # x1, y1, x2, y2 (pixel coords)
    confidence: float


# 列宽容差：两个字符 X 中心点差距在此范围内视为同一列（像素）
_COLUMN_TOLERANCE = 30


# ---------------------------------------------------------------------------
# 竖排排序（与后端无关）
# ---------------------------------------------------------------------------

def sort_vertical_chars(chars: list[CharResult]) -> list[CharResult]:
    """将字符按竖排顺序排序：列从右到左，列内从上到下。"""
    if not chars:
        return []

    def x_center(c: CharResult) -> float:
        return (c.bbox[0] + c.bbox[2]) / 2

    def y_center(c: CharResult) -> float:
        return (c.bbox[1] + c.bbox[3]) / 2

    sorted_by_x = sorted(chars, key=x_center, reverse=True)

    columns: list[list[CharResult]] = []
    for char in sorted_by_x:
        cx = x_center(char)
        placed = False
        for col in columns:
            if abs(x_center(col[0]) - cx) <= _COLUMN_TOLERANCE:
                col.append(char)
                placed = True
                break
        if not placed:
            columns.append([char])

    result: list[CharResult] = []
    for col in columns:
        result.extend(sorted(col, key=y_center))
    return result


# ---------------------------------------------------------------------------
# 后端：百度智能云 OCR（国内首选）
# ---------------------------------------------------------------------------

_baidu_client = None


def _get_baidu_client():
    """返回百度 AipOcr 客户端单例。"""
    global _baidu_client
    if _baidu_client is None:
        from aip import AipOcr
        _baidu_client = AipOcr(
            os.environ["BAIDU_OCR_APP_ID"],
            os.environ["BAIDU_OCR_API_KEY"],
            os.environ["BAIDU_OCR_SECRET_KEY"],
        )
    return _baidu_client


def _recognize_baidu(
    image_bytes: bytes,
    region_bbox: tuple[int, int, int, int],
    confidence_threshold: float,
) -> list[CharResult]:
    """调用百度 OCR 高精度含位置版识别。

    使用 accurate() 接口：高精度识别 + 返回 location 坐标。
    百度按"词"返回，逐字均摊坐标以还原单字 bbox。
    """
    client = _get_baidu_client()
    options = {
        "detect_direction": "true",   # 自动检测文字方向（含竖排）
        "probability": "true",        # 返回置信度
    }
    resp = client.accurate(image_bytes, options)

    ox, oy = region_bbox[0], region_bbox[1]
    results: list[CharResult] = []

    for word_info in resp.get("words_result", []):
        text = word_info.get("words", "")
        prob = word_info.get("probability", {}).get("average", 1.0)
        if prob < confidence_threshold:
            continue

        loc = word_info.get("location", {})
        x1 = int(loc.get("left", 0)) + ox
        y1 = int(loc.get("top", 0)) + oy
        x2 = x1 + int(loc.get("width", 0))
        y2 = y1 + int(loc.get("height", 0))

        # 百度按词返回，逐字拆分（均摊 x 坐标，竖排时均摊 y）
        n = len(text)
        if n == 0:
            continue
        char_h = (y2 - y1) / n if n > 1 else (y2 - y1)
        for i, ch in enumerate(text):
            cy1 = int(y1 + i * char_h)
            cy2 = int(y1 + (i + 1) * char_h)
            results.append(CharResult(
                text=ch,
                bbox=(x1, cy1, x2, cy2),
                confidence=float(prob),
            ))

    return results


# ---------------------------------------------------------------------------
# 后端：腾讯云 OCR
# ---------------------------------------------------------------------------

def _recognize_tencent(
    image_bytes: bytes,
    region_bbox: tuple[int, int, int, int],
    confidence_threshold: float,
) -> list[CharResult]:
    """调用腾讯云 GeneralAccurateOCR（通用印刷体识别（高精度版））。"""
    from tencentcloud.common import credential
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
    from tencentcloud.ocr.v20181119 import ocr_client, models

    secret_id = os.environ["TENCENT_SECRET_ID"]
    secret_key = os.environ["TENCENT_SECRET_KEY"]
    region = os.environ.get("TENCENT_REGION", "ap-guangzhou")

    cred = credential.Credential(secret_id, secret_key)
    client = ocr_client.OcrClient(cred, region)

    req = models.GeneralAccurateOCRRequest()
    req.ImageBase64 = base64.b64encode(image_bytes).decode()

    resp = client.GeneralAccurateOCR(req)

    ox, oy = region_bbox[0], region_bbox[1]
    results: list[CharResult] = []

    for item in resp.TextDetections:
        text = item.DetectedText
        # 腾讯返回多边形顶点
        pts = item.ItemPolygon
        x1 = pts.X + ox
        y1 = pts.Y + oy
        x2 = x1 + pts.Width
        y2 = y1 + pts.Height
        n = len(text)
        if n == 0:
            continue
        char_h = (y2 - y1) / n if n > 1 else (y2 - y1)
        for i, ch in enumerate(text):
            results.append(CharResult(
                text=ch,
                bbox=(x1, int(y1 + i * char_h), x2, int(y1 + (i + 1) * char_h)),
                confidence=0.95,   # 腾讯通用版不返回置信度，默认 0.95
            ))

    return results


# ---------------------------------------------------------------------------
# 后端：Google Cloud Vision（保留，科学上网环境可用）
# ---------------------------------------------------------------------------

_vision_client_instance = None


def _get_vision_client():
    global _vision_client_instance
    if _vision_client_instance is None:
        from google.cloud import vision
        _vision_client_instance = vision.ImageAnnotatorClient()
    return _vision_client_instance


def _recognize_google(
    image_bytes: bytes,
    region_bbox: tuple[int, int, int, int],
    confidence_threshold: float,
) -> list[CharResult]:
    """调用 Google Cloud Vision DOCUMENT_TEXT_DETECTION。"""
    client = _get_vision_client()
    try:
        from google.cloud import vision as _vision
        image = _vision.Image(content=image_bytes)
        image_context = _vision.ImageContext(language_hints=["zh-TW"])
        response = client.document_text_detection(image=image, image_context=image_context)
    except ModuleNotFoundError:
        response = client.document_text_detection(
            image={"content": image_bytes},
            image_context={"language_hints": ["zh-TW"]},
        )

    ox, oy = region_bbox[0], region_bbox[1]
    results: list[CharResult] = []
    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            for para in block.paragraphs:
                for word in para.words:
                    for symbol in word.symbols:
                        conf = symbol.confidence
                        if conf < confidence_threshold:
                            continue
                        verts = symbol.bounding_box.vertices
                        xs = [v.x for v in verts]
                        ys = [v.y for v in verts]
                        results.append(CharResult(
                            text=symbol.text,
                            bbox=(min(xs)+ox, min(ys)+oy, max(xs)+ox, max(ys)+oy),
                            confidence=conf,
                        ))
    return results


# ---------------------------------------------------------------------------
# 统一入口（根据 OCR_BACKEND 环境变量路由）
# ---------------------------------------------------------------------------

def recognize_region(
    image_bytes: bytes,
    region_bbox: tuple[int, int, int, int],
    confidence_threshold: float = 0.7,
) -> list[CharResult]:
    """对指定区域进行 OCR，返回字符结果列表（未排序）。

    通过环境变量 OCR_BACKEND 选择后端：
        baidu（默认）| tencent | google

    Args:
        image_bytes: PNG/JPEG bytes。
        region_bbox: 在原始页面的坐标 (x1,y1,x2,y2)，用于偏移转换。
        confidence_threshold: 低于此值的字符被过滤。
    """
    backend = os.environ.get("OCR_BACKEND", "baidu").lower()

    if backend == "baidu":
        return _recognize_baidu(image_bytes, region_bbox, confidence_threshold)
    elif backend == "tencent":
        return _recognize_tencent(image_bytes, region_bbox, confidence_threshold)
    elif backend == "google":
        return _recognize_google(image_bytes, region_bbox, confidence_threshold)
    else:
        raise ValueError(
            f"不支持的 OCR_BACKEND: '{backend}'，"
            "可选值：baidu | tencent | google"
        )
