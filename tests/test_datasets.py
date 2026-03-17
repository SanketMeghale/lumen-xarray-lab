from __future__ import annotations

import xarray as xr

from lumen_xarray_lab.datasets import apply_query_to_array, estimate_query_cost, sample_table_dataframe


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
