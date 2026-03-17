from __future__ import annotations

from lumen_xarray_lab.ai_hooks import build_ai_context, build_cli_example, infer_xarray_engine, is_xarray_path


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


def test_build_ai_context_generates_dataset_aware_prompts(multi_table_dataset):
    context = build_ai_context(
        multi_table_dataset,
        table="temperature",
        coord_map={"time": "time", "latitude": None, "longitude": None, "vertical": None},
    )

    assert context["table"] == "temperature"
    assert "time_analysis" in context["capabilities"]
    assert "compare" in context["capabilities"]
    assert any("rolling mean" in prompt for prompt in context["suggested_prompts"])
