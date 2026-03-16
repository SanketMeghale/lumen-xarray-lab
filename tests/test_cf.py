from __future__ import annotations

from lumen_xarray_lab.cf import detect_coordinates, get_coordinate_metadata


def test_detect_coordinates(synthetic_dataset):
    coords = detect_coordinates(synthetic_dataset)
    assert coords["time"] == "time"
    assert coords["latitude"] == "lat"
    assert coords["longitude"] == "lon"


def test_get_coordinate_metadata(synthetic_dataset):
    meta = get_coordinate_metadata(synthetic_dataset)
    assert meta["lat"]["role"] == "latitude"
    assert meta["time"]["dtype"].startswith("datetime64")
