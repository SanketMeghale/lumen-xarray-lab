from __future__ import annotations

import cftime
import numpy as np
import pandas as pd
import xarray as xr

from lumen_xarray_lab.datasets import (
    LabXarraySourceAdapter,
    apply_query_to_array,
    estimate_query_cost,
    make_dataframe_panel_safe,
    sample_table_dataframe,
)


def test_sample_table_dataframe_returns_empty_frame_for_empty_selection(synthetic_dataset):
    frame = sample_table_dataframe(
        synthetic_dataset,
        "temperature",
        query={"lat": (99.0, 100.0)},
        limit=25,
    )

    assert list(frame.columns) == ["time", "lat", "lon", "temperature"]
    assert frame.empty


def test_estimate_query_cost_reflects_filtered_selection(synthetic_dataset):
    estimate = estimate_query_cost(
        synthetic_dataset,
        "temperature",
        query={"lat": (10.0, 10.0)},
    )

    assert estimate["selected_rows"] == 4
    assert estimate["full_rows"] == 8
    assert estimate["selection_ratio"] == 0.5
    assert estimate["column_count"] == 4
    assert estimate["approx_dataframe_mb"] >= 0.0


def test_apply_query_to_array_handles_descending_coordinates():
    arr = xr.DataArray(
        [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
        dims=("lat", "lon"),
        coords={"lat": [20.0, 10.0, 0.0], "lon": [100.0, 110.0]},
        name="sst",
    )

    filtered = apply_query_to_array(arr, query={"lat": (0.0, 10.0)})

    assert list(filtered["lat"].values) == [10.0, 0.0]
    assert filtered.shape == (2, 2)


def test_sample_table_dataframe_keeps_curvilinear_role_columns():
    dataset = xr.Dataset(
        data_vars={"sst": (("y", "x"), np.arange(6.0).reshape(2, 3))},
        coords={
            "yc": xr.DataArray(
                np.array([[42.0, 42.5, 43.0], [41.0, 41.5, 42.0]]),
                dims=("y", "x"),
                attrs={"long_name": "latitude of grid cell center", "units": "degrees_north"},
            ),
            "xc": xr.DataArray(
                np.array([[210.0, 211.0, 212.0], [210.5, 211.5, 212.5]]),
                dims=("y", "x"),
                attrs={"long_name": "longitude of grid cell center", "units": "degrees_east"},
            ),
        },
    )

    frame = sample_table_dataframe(dataset, "sst", limit=10)

    assert "yc" in frame.columns
    assert "xc" in frame.columns
    assert "sst" in frame.columns


def test_lab_source_adapter_combines_multi_file_glob(tmp_path, synthetic_dataset):
    part_one = synthetic_dataset.isel(time=slice(0, 1)).copy(deep=True)
    part_two = synthetic_dataset.isel(time=slice(1, 2)).copy(deep=True)
    first = tmp_path / "part_01.nc"
    second = tmp_path / "part_02.nc"
    for dataset, target in ((part_one, first), (part_two, second)):
        for variable in dataset.variables:
            dataset[variable].encoding = {}
        dataset.to_netcdf(target)

    source = LabXarraySourceAdapter(uri=str(tmp_path / "*.nc"))

    assert source.source_mode == "multi-file"
    assert len(source.source_uris) == 2
    frame = source.get("temperature")
    assert len(frame) == 8


def test_make_dataframe_panel_safe_normalizes_cftime_columns():
    frame = pd.DataFrame(
        {
            "time": [
                cftime.DatetimeNoLeap(2001, 1, 1),
                cftime.DatetimeNoLeap(2001, 2, 1),
            ],
            "temperature": [280.0, 281.5],
        }
    )

    safe = make_dataframe_panel_safe(frame)

    assert not any(type(value).__module__.startswith("cftime") for value in safe["time"].dropna())
