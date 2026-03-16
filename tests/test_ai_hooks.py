from __future__ import annotations

from lumen_xarray_lab.ai_hooks import build_cli_example, infer_xarray_engine, is_xarray_path


def test_is_xarray_path():
    assert is_xarray_path("data.nc")
    assert is_xarray_path("data.zarr")
    assert not is_xarray_path("data.csv")


def test_build_cli_example():
    assert build_cli_example("data.nc") == "lumen-ai serve data.nc"


def test_infer_xarray_engine():
    assert infer_xarray_engine("data.nc") == "netcdf"
    assert infer_xarray_engine("data.zarr") == "zarr"
    assert infer_xarray_engine("data.csv") is None
