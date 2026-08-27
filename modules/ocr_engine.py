"""OCR 模块：支持多云端 OCR 后端（百度/腾讯/阿里/Google）。

通过环境变量 OCR_BACKEND 切换后端（默认 baidu）：
    set OCR_BACKEND=baidu    # 百度智能云（推荐，国内首选）
    set OCR_BACKEND=tencent  # 腾讯云
    set OCR_BACKEND=google   # Google Cloud Vision（需科学上网）

百度接口（OCR_BACKEND=baidu 时）：
    默认 client.accurate() 高精度含位置
    --paddle-vl 或 BAIDU_OCR_API=paddle-vl → 文档解析 PaddleOCR-VL

各后端所需环境变量：
    百度:   BAIDU_OCR_APP_ID, BAIDU_OCR_API_KEY, BAIDU_OCR_SECRET_KEY
    腾讯:   TENCENT_SECRET_ID, TENCENT_SECRET_KEY, TENCENT_REGION(可选)
    Google: GOOGLE_APPLICATION_CREDENTIALS
"""
from __future__ import annotations
import base64
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
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

log = logging.getLogger(__name__)


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


def _baidu_loc_xyxy(loc: dict, ox: int, oy: int) -> tuple[int, int, int, int]:
    x1 = int(loc.get("left", 0)) + ox
    y1 = int(loc.get("top", 0)) + oy
    x2 = x1 + int(loc.get("width", 0))
    y2 = y1 + int(loc.get("height", 0))
    return x1, y1, x2, y2


def _baidu_word_to_chars(
    word_info: dict,
    ox: int,
    oy: int,
    confidence_threshold: float,
) -> list[CharResult]:
    """把百度 words_result 一项拆成单字。优先用 recognize_granularity=small 的 chars[]。"""
    text = word_info.get("words", "") or ""
    prob = float(word_info.get("probability", {}).get("average", 1.0))
    results: list[CharResult] = []

    for item in word_info.get("chars") or []:
        ch = str(item.get("char") or item.get("words") or "")
        if not ch:
            continue
        cprob = item.get("probability")
        if isinstance(cprob, dict):
            cprob = float(cprob.get("average", prob))
        elif cprob is None:
            cprob = prob
        else:
            cprob = float(cprob)
        if cprob < confidence_threshold:
            continue
        loc = item.get("location") or word_info.get("location") or {}
        x1, y1, x2, y2 = _baidu_loc_xyxy(loc, ox, oy)
        results.append(CharResult(text=ch, bbox=(x1, y1, x2, y2), confidence=cprob))
    if results:
        return results

    if not text or prob < confidence_threshold:
        return []
    x1, y1, x2, y2 = _baidu_loc_xyxy(word_info.get("location") or {}, ox, oy)
    n = len(text)
    w, h = x2 - x1, y2 - y1
    if n <= 1 or w <= 0 or h <= 0:
        return [CharResult(text=text, bbox=(x1, y1, x2, y2), confidence=prob)]

    # 无单字框时：横条按 x 均摊，竖条按 y 均摊（旧逻辑一律切 y，横排会错位）
    if w >= h:
        step = w / n
        for i, ch in enumerate(text):
            results.append(CharResult(
                text=ch,
                bbox=(int(x1 + i * step), y1, int(x1 + (i + 1) * step), y2),
                confidence=prob,
            ))
    else:
        step = h / n
        for i, ch in enumerate(text):
            results.append(CharResult(
                text=ch,
                bbox=(x1, int(y1 + i * step), x2, int(y1 + (i + 1) * step)),
                confidence=prob,
            ))
    return results


def _recognize_baidu(
    image_bytes: bytes,
    region_bbox: tuple[int, int, int, int],
    confidence_threshold: float,
) -> list[CharResult]:
    """调用百度 OCR 高精度含位置版识别。

    使用 accurate()：高精度 + 单字位置（recognize_granularity=small）。
    """
    client = _get_baidu_client()
    options = {
        "detect_direction": "true",
        "probability": "true",
        "recognize_granularity": "small",
    }
    resp = client.accurate(image_bytes, options)
    err = _baidu_api_error(resp)
    if err:
        log.warning(f"百度 accurate 失败: {err}")
        return []

    ox, oy = region_bbox[0], region_bbox[1]
    results: list[CharResult] = []
    for word_info in resp.get("words_result", []):
        results.extend(_baidu_word_to_chars(word_info, ox, oy, confidence_threshold))
    return results


# ---------------------------------------------------------------------------
# 后端：百度文档解析 PaddleOCR-VL（异步）
# https://cloud.baidu.com/doc/OCR/s/7mh8u7ruk
# ---------------------------------------------------------------------------

_BAIDU_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
_BAIDU_PADDLE_VL_TASK = (
    "https://aip.baidubce.com/rest/2.0/brain/online/v2/paddle-vl-parser/task"
)
_BAIDU_PADDLE_VL_QUERY = (
    "https://aip.baidubce.com/rest/2.0/brain/online/v2/paddle-vl-parser/task/query"
)

_baidu_token: tuple[str, float] | None = None  # (token, expire_epoch)


def enable_paddle_vl(enabled: bool = True) -> None:
    """CLI --paddle-vl：改用百度 PaddleOCR-VL，其余识别流程不变。"""
    if enabled:
        os.environ["BAIDU_OCR_API"] = "paddle-vl"
    else:
        os.environ.pop("BAIDU_OCR_API", None)


def _use_baidu_paddle_vl() -> bool:
    val = os.environ.get("BAIDU_OCR_API", "").lower().replace("_", "-")
    return val in ("paddle-vl", "paddleocr-vl", "paddlevl")


def _http_json(url: str, data: dict | None = None, timeout: int = 60) -> dict:
    body = None
    headers = {}
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"百度 API HTTP {e.code}: {detail}") from e


def _baidu_api_error(payload: dict) -> str | None:
    code = payload.get("error_code")
    if code in (None, 0, "0", ""):
        return None
    return str(payload.get("error_msg") or code)


def _baidu_access_token() -> str:
    global _baidu_token
    now = time.time()
    if _baidu_token and _baidu_token[1] > now + 60:
        return _baidu_token[0]
    params = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": os.environ["BAIDU_OCR_API_KEY"],
        "client_secret": os.environ["BAIDU_OCR_SECRET_KEY"],
    })
    payload = _http_json(f"{_BAIDU_TOKEN_URL}?{params}")
    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"获取百度 access_token 失败: {payload}")
    expires = now + float(payload.get("expires_in", 2592000))
    _baidu_token = (token, expires)
    return token


def _iter_nums(obj):
    if isinstance(obj, (int, float)):
        yield float(obj)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            yield from _iter_nums(item)


def _box_to_xyxy(box, ox: int, oy: int) -> tuple[int, int, int, int]:
    """position / location / polygon → (x1, y1, x2, y2)。"""
    if isinstance(box, dict):
        x = int(box.get("left", box.get("x", 0)))
        y = int(box.get("top", box.get("y", 0)))
        w = int(box.get("width", box.get("w", 0)))
        h = int(box.get("height", box.get("h", 0)))
        if "x2" in box:
            return x + ox, y + oy, int(box["x2"]) + ox, int(box.get("y2", y + h)) + oy
        return x + ox, y + oy, x + w + ox, y + h + oy
    nums = list(_iter_nums(box))
    if len(nums) >= 8:
        xs, ys = nums[0::2], nums[1::2]
        return (
            int(min(xs)) + ox, int(min(ys)) + oy,
            int(max(xs)) + ox, int(max(ys)) + oy,
        )
    if len(nums) >= 4:
        x, y, a, b = nums[:4]
        return int(x) + ox, int(y) + oy, int(x + a) + ox, int(y + b) + oy
    return ox, oy, ox, oy


def _chars_from_text_box(
    text: str,
    bbox: tuple[int, int, int, int],
    confidence: float,
    vertical: bool,
) -> list[CharResult]:
    text = (text or "").strip()
    if not text:
        return []
    x1, y1, x2, y2 = bbox
    n = len(text)
    if n == 1:
        return [CharResult(text=text, bbox=bbox, confidence=confidence)]
    w, h = max(x2 - x1, 1), max(y2 - y1, 1)
    split_y = vertical or (h >= w)
    results: list[CharResult] = []
    if split_y:
        step = h / n
        for i, ch in enumerate(text):
            cy1 = int(y1 + i * step)
            cy2 = int(y1 + (i + 1) * step)
            results.append(CharResult(text=ch, bbox=(x1, cy1, x2, cy2), confidence=confidence))
    else:
        step = w / n
        for i, ch in enumerate(text):
            cx1 = int(x1 + i * step)
            cx2 = int(x1 + (i + 1) * step)
            results.append(CharResult(text=ch, bbox=(cx1, y1, cx2, y2), confidence=confidence))
    return results


def _span_text(span: dict) -> str:
    raw = span.get("text", "")
    if isinstance(raw, list):
        return "".join(str(t) for t in raw)
    return str(raw or "")


_SKIP_LAYOUT_TYPES = {
    "image", "header_image", "footer_image", "chart", "footer", "header",
}


def paddle_vl_pages_to_chars(
    pages: list,
    ox: int,
    oy: int,
    confidence_threshold: float,
) -> list[CharResult]:
    """把 PaddleOCR-VL 的 pages[].layouts 转成 CharResult（供测试与识别共用）。"""
    results: list[CharResult] = []
    conf = 0.99 if 0.99 >= confidence_threshold else 1.0
    if conf < confidence_threshold:
        return []
    for page in pages or []:
        for layout in page.get("layouts") or []:
            ltype = str(layout.get("type") or "")
            if ltype in _SKIP_LAYOUT_TYPES:
                continue
            vertical = ltype == "vertical_text"
            spans = layout.get("span_boxes") or []
            if spans:
                for span in spans:
                    text = _span_text(span)
                    loc = span.get("location") or span.get("position") or layout.get("position")
                    bbox = _box_to_xyxy(loc, ox, oy)
                    results.extend(_chars_from_text_box(text, bbox, conf, vertical))
                continue
            text = str(layout.get("text") or "").strip()
            pos = layout.get("position")
            if text and pos:
                results.extend(_chars_from_text_box(
                    text, _box_to_xyxy(pos, ox, oy), conf, vertical,
                ))
            if ltype == "table":
                for cell in (page.get("tables") or []):
                    if cell.get("layout_id") != layout.get("layout_id"):
                        continue
                    for c in cell.get("cells") or []:
                        ct = str(c.get("text") or "").strip()
                        cpos = c.get("position") or pos
                        if ct and cpos:
                            results.extend(_chars_from_text_box(
                                ct, _box_to_xyxy(cpos, ox, oy), conf, False,
                            ))
    return results


def _recognize_baidu_paddle_vl(
    image_bytes: bytes,
    region_bbox: tuple[int, int, int, int],
    confidence_threshold: float,
) -> list[CharResult]:
    """调用百度文档解析 PaddleOCR-VL（提交任务 + 轮询 + 下载 JSON）。"""
    token = _baidu_access_token()
    fname = "page.jpg" if image_bytes[:2] == b"\xff\xd8" else "page.png"
    submit = _http_json(
        f"{_BAIDU_PADDLE_VL_TASK}?access_token={urllib.parse.quote(token)}",
        {
            "file_data": base64.b64encode(image_bytes).decode("ascii"),
            "file_name": fname,
            "return_span_boxes": "true",
        },
        timeout=120,
    )
    err = _baidu_api_error(submit)
    if err:
        raise RuntimeError(f"PaddleOCR-VL 提交失败: {err}")
    task_id = (submit.get("result") or {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"PaddleOCR-VL 未返回 task_id: {submit}")
    log.info(f"PaddleOCR-VL 任务已提交: {task_id}")

    deadline = time.time() + 180
    time.sleep(5)
    result_meta: dict = {}
    while time.time() < deadline:
        queried = _http_json(
            f"{_BAIDU_PADDLE_VL_QUERY}?access_token={urllib.parse.quote(token)}",
            {"task_id": task_id},
            timeout=60,
        )
        err = _baidu_api_error(queried)
        if err:
            raise RuntimeError(f"PaddleOCR-VL 查询失败: {err}")
        result_meta = queried.get("result") or {}
        status = str(result_meta.get("status") or "")
        if status == "success":
            break
        if status == "failed":
            raise RuntimeError(
                f"PaddleOCR-VL 任务失败: {result_meta.get('task_error')}"
            )
        time.sleep(3)
    else:
        raise RuntimeError(f"PaddleOCR-VL 等待超时: {task_id}")

    pages = result_meta.get("pages")
    if not pages:
        url = result_meta.get("parse_result_url")
        if not url:
            raise RuntimeError(f"PaddleOCR-VL 无解析结果: {result_meta}")
        parsed = _http_json(url, data=None, timeout=60)
        pages = parsed.get("pages") or []

    ox, oy = region_bbox[0], region_bbox[1]
    return paddle_vl_pages_to_chars(pages, ox, oy, confidence_threshold)

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
        if _use_baidu_paddle_vl():
            return _recognize_baidu_paddle_vl(
                image_bytes, region_bbox, confidence_threshold,
            )
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
