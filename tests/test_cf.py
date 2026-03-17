from __future__ import annotations

import numpy as np
import xarray as xr

from lumen_xarray_lab.cf import detect_coordinates, get_coordinate_metadata


def test_detect_coordinates(synthetic_dataset):
    coords = detect_coordinates(synthetic_dataset)
    assert coords["time"] == "time"
    assert coords["latitude"] == "lat"
    assert coords["longitude"] == "lon"
    assert coords["vertical"] is None


def test_detect_coordinates_prefers_cf_attributes():
    dataset = xr.Dataset(
        data_vars={
            "air": (("forecast_reference_time", "y", "x"), np.ones((2, 2, 2))),
        },
        coords={
            "forecast_reference_time": xr.DataArray(
                np.array([0, 6]),
                dims=("forecast_reference_time",),
                attrs={"standard_name": "time", "units": "hours since 2024-01-01 00:00:00", "axis": "T"},
            ),
            "y": xr.DataArray(
                np.array([10.0, 20.0]),
                dims=("y",),
                attrs={"units": "degrees_north", "axis": "Y", "long_name": "grid latitude"},
            ),
            "x": xr.DataArray(
                np.array([70.0, 80.0]),
                dims=("x",),
                attrs={"units": "degrees_east", "axis": "X", "long_name": "grid longitude"},
            ),
            "isobaric": xr.DataArray(
                np.array([1000.0, 850.0]),
                dims=("isobaric",),
                attrs={"standard_name": "air_pressure", "units": "hPa", "positive": "down", "axis": "Z"},
            ),
        },
    )

    coords = detect_coordinates(dataset)

    assert coords["time"] == "forecast_reference_time"
    assert coords["latitude"] == "y"
    assert coords["longitude"] == "x"
    assert coords["vertical"] == "isobaric"


def test_detect_coordinates_does_not_promote_generic_xy_without_geospatial_hints():
    dataset = xr.Dataset(
        data_vars={
            "intensity": (("y", "x"), np.array([[1.0, 2.0], [3.0, 4.0]])),
        },
        coords={
            "x": np.array([0.0, 1.0]),
            "y": np.array([0.0, 1.0]),
        },
    )

    coords = detect_coordinates(dataset)

    assert coords["latitude"] is None
    assert coords["longitude"] is None


def test_get_coordinate_metadata_exposes_detection_details(synthetic_dataset):
    meta = get_coordinate_metadata(synthetic_dataset)

    assert meta["lat"]["role"] == "latitude"
    assert meta["lat"]["selected"] is True
    assert meta["lat"]["confidence"] in {"medium", "high"}
    assert meta["time"]["dtype"].startswith("datetime64")
    assert meta["time"]["detection_score"] >= 8
    assert meta["time"]["detection_reasons"]


def test_get_coordinate_metadata_marks_curvilinear_map_candidates():
    dataset = xr.Dataset(
        data_vars={
            "sst": (("y", "x"), np.arange(6.0).reshape(2, 3)),
        },
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

    coords = detect_coordinates(dataset)
    meta = get_coordinate_metadata(dataset)

    assert coords["latitude"] == "yc"
    assert coords["longitude"] == "xc"
    assert meta["yc"]["curvilinear"] is True
    assert meta["xc"]["map_candidate"] is True
