from __future__ import annotations
import io
import logging
import os
import yaml
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from modules.page_model import PageData, TextColumn, CharData, ImageRegion

_registered_fonts: set = set()

def _register_font(font_family, font_path):
    if font_family not in _registered_fonts:
        if os.path.exists(font_path):
            # .ttc 容器需指定子字体索引（取第 0 个）
            if font_path.lower().endswith(".ttc"):
                font_obj = TTFont(font_family, font_path, subfontIndex=0)
            else:
                font_obj = TTFont(font_family, font_path)
            pdfmetrics.registerFont(font_obj)
            _registered_fonts.add(font_family)
            logging.info(f"字体已注册: {font_family} <- {font_path}")
        else:
            logging.warning(
                f"字体文件不存在: {font_path}，将使用内置 Helvetica（中文会显示方块）。"
                f" 请在 config/layout_config.yaml 中配置正确的 font_path。"
            )

def load_config(config_path='config/layout_config.yaml'):
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def _px_to_pt(px, dpi):
    return px * 72.0 / dpi

def _scale_bbox(bbox, dpi, pdf_page_h):
    x1, y1, x2, y2 = bbox
    x_pt = _px_to_pt(x1, dpi)
    y_pt_top = _px_to_pt(y1, dpi)
    w_pt = _px_to_pt(x2 - x1, dpi)
    h_pt = _px_to_pt(y2 - y1, dpi)
    y_bottom = pdf_page_h - y_pt_top - h_pt
    return x_pt, y_bottom, w_pt, h_pt

def _draw_vertical_column(c, column, dpi, pdf_page_h, font_family, font_size):
    for char in column.chars:
        x1, y1, x2, y2 = char.bbox
        cx_pt = _px_to_pt((x1 + x2) / 2, dpi)
        cy_pt = pdf_page_h - _px_to_pt((y1 + y2) / 2, dpi)
        x_draw = cx_pt - _px_to_pt((x2 - x1) / 2, dpi)
        y_draw = cy_pt - font_size / 2
        try:
            c.setFont(font_family, font_size)
        except Exception:
            c.setFont('Helvetica', font_size)
        c.drawString(x_draw, y_draw, char.text)

def _draw_image_region(c, region, dpi, pdf_page_h, image_scale):
    from reportlab.lib.utils import ImageReader
    x_pt, y_bottom, w_pt, h_pt = _scale_bbox(region.bbox, dpi, pdf_page_h)
    c.drawImage(ImageReader(io.BytesIO(region.image_bytes)),
                x_pt, y_bottom, width=w_pt * image_scale,
                height=h_pt * image_scale,
                preserveAspectRatio=True, mask='auto')

def create_pdf(pages, output_path, config):
    font_family = config.get('font_family', 'Helvetica')
    font_path   = config.get('font_path', '')
    font_size   = float(config.get('font_size', 14))
    image_scale = float(config.get('image_scale', 1.0))
    page_size_cfg = config.get('page_size', 'original')
    _register_font(font_family, font_path)
    default_page_size = A4 if page_size_cfg == 'A4' else None
    c = canvas.Canvas(output_path)
    for page in pages:
        dpi = page.dpi
        if default_page_size:
            pw, ph = default_page_size
        else:
            pw = _px_to_pt(page.orig_width_px, dpi)
            ph = _px_to_pt(page.orig_height_px, dpi)
        c.setPageSize((pw, ph))
        for region in page.image_regions:
            _draw_image_region(c, region, dpi, ph, image_scale)
        for col in page.text_columns:
            _draw_vertical_column(c, col, dpi, ph, font_family, font_size)
        c.showPage()
    c.save()
