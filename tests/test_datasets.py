from __future__ import annotations

from lumen_xarray_lab.datasets import sample_table_dataframe


def test_sample_table_dataframe_returns_empty_frame_for_empty_selection(synthetic_dataset):
    frame = sample_table_dataframe(
        synthetic_dataset,
        "temperature",
        query={"lat": (99.0, 100.0)},
        limit=25,
    )

    assert list(frame.columns) == ["time", "lat", "lon", "temperature"]
    assert frame.empty
