from __future__ import annotations

from lumen_xarray_lab.benchmark_utils import (
    estimate_dataframe_bytes,
    estimate_flattened_rows,
    estimate_row_explosion,
    format_bytes,
    write_benchmark_report,
)


def test_estimate_flattened_rows():
    assert estimate_flattened_rows({"time": 2, "lat": 3, "lon": 4}) == 24


def test_estimate_dataframe_bytes():
    assert estimate_dataframe_bytes(10, 5) == 400


def test_estimate_row_explosion():
    assert estimate_row_explosion(2, 20) == 10.0


def test_format_bytes():
    assert format_bytes(1024) == "1.00 KB"


def test_write_benchmark_report(tmp_path):
    target = write_benchmark_report("demo", {"rows": 10}, tmp_path)
    assert target.exists()
    assert target.read_text(encoding="utf-8").strip().startswith("{")
