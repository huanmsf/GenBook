"""tests/test_main.py"""
import os
import re
import pytest
from main import parse_args, build_output_path, parse_pages


def test_parse_args_input_pdf_required():
    with pytest.raises(SystemExit):
        parse_args([])


def test_parse_args_defaults():
    args = parse_args(["input/test.pdf"])
    assert args.input_pdf == "input/test.pdf"
    assert args.output_pdf is None
    assert args.pages is None
    assert args.dpi == 300


def test_parse_args_pages_range():
    args = parse_args(["a.pdf", "--pages", "3-10"])
    assert args.pages == "3-10"


def test_parse_args_output_name():
    args = parse_args(["a.pdf", "--output", "my_result.pdf"])
    assert args.output_pdf == "my_result.pdf"


def test_build_output_path_custom_name():
    result = build_output_path("input/test.pdf", output_name="my_out.pdf")
    assert result == os.path.join("output", "my_out.pdf")


def test_build_output_path_default_name():
    result = build_output_path("input/book.pdf")
    expected_prefix = os.path.join("output", "book_out_")
    assert result.startswith(expected_prefix)
    assert result.endswith(".pdf")
    assert re.search(r"_out_\d{14}\.pdf$", result)


def test_parse_pages_range():
    start, end = parse_pages("3-10")
    assert start == 3
    assert end == 10


def test_parse_pages_none():
    start, end = parse_pages(None)
    assert start is None
    assert end is None


def test_parse_pages_invalid_raises():
    with pytest.raises(ValueError):
        parse_pages("abc")


def test_parse_pages_start_gt_end_raises():
    with pytest.raises(ValueError):
        parse_pages("10-3")
