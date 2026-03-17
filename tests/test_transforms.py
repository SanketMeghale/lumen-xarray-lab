from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

from lumen_xarray_lab.transforms import apply_transform


def _monthly_dataset() -> xr.Dataset:
    time = pd.date_range("2024-01-01", periods=6, freq="MS")
    lat = np.array([10.0, 20.0])
    lon = np.array([70.0, 80.0])
    values = np.arange(24.0).reshape(6, 2, 2)
    dataset = xr.Dataset(
        data_vars={"temperature": (("time", "lat", "lon"), values)},
        coords={"time": time, "lat": lat, "lon": lon},
    )
    dataset["lat"].attrs["units"] = "degrees_north"
    dataset["lon"].attrs["units"] = "degrees_east"
    return dataset


def test_apply_transform_rolling_mean_preserves_time_dimension():
    dataset = _monthly_dataset()

    result = apply_transform(
        dataset["temperature"],
        {"time": "time", "latitude": "lat", "longitude": "lon", "vertical": None},
        transform="rolling mean",
        window=3,
    )

    assert result.summary["window"] == 3
    assert "time" in result.array.dims
    assert result.array.shape == dataset["temperature"].shape


def test_apply_transform_resample_reduces_time_points():
    dataset = _monthly_dataset()

    result = apply_transform(
        dataset["temperature"],
        {"time": "time", "latitude": "lat", "longitude": "lon", "vertical": None},
        transform="resample",
        aggregation="mean",
        resample_rule="QS-DEC",
    )

    assert "time" in result.array.dims
    assert int(result.array.sizes["time"]) == 3


def test_apply_transform_climatology_creates_month_dimension():
    dataset = _monthly_dataset()

    result = apply_transform(
        dataset["temperature"],
        {"time": "time", "latitude": "lat", "longitude": "lon", "vertical": None},
        transform="climatology",
        aggregation="mean",
    )

    assert "month" in result.array.dims
    assert int(result.array.sizes["month"]) == 6


def test_apply_transform_spatial_mean_reduces_lat_lon():
    dataset = _monthly_dataset()

    result = apply_transform(
        dataset["temperature"],
        {"time": "time", "latitude": "lat", "longitude": "lon", "vertical": None},
        transform="spatial mean",
        aggregation="mean",
    )

    assert result.summary["reduced_dims"] == ["lat", "lon"]
    assert result.array.dims == ("time",)


def test_apply_transform_zonal_mean_reduces_longitude_only():
    dataset = _monthly_dataset()

    result = apply_transform(
        dataset["temperature"],
        {"time": "time", "latitude": "lat", "longitude": "lon", "vertical": None},
        transform="zonal mean",
        aggregation="mean",
    )

    assert result.summary["reduced_dims"] == ["lon"]
    assert result.array.dims == ("time", "lat")
