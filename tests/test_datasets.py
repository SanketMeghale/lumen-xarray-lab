from __future__ import annotations

from lumen_xarray_lab.datasets import estimate_query_cost, sample_table_dataframe


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
