from __future__ import annotations

from typing import Any

import xarray as xr

LAT_NAMES = {"lat", "latitude", "y"}
LON_NAMES = {"lon", "longitude", "x"}
TIME_NAMES = {"time", "date", "datetime"}
VERTICAL_NAMES = {"level", "lev", "depth", "height", "z", "pressure"}


def _coord_role(name: str, coord: xr.DataArray) -> str | None:
    lower = name.lower()
    attrs = {str(k).lower(): str(v).lower() for k, v in coord.attrs.items()}
    units = attrs.get("units", "")
    standard_name = attrs.get("standard_name", "")

    if lower in LAT_NAMES or "degrees_north" in units or standard_name == "latitude":
        return "latitude"
    if lower in LON_NAMES or "degrees_east" in units or standard_name == "longitude":
        return "longitude"
    if lower in TIME_NAMES or "time" in standard_name or str(coord.dtype).startswith("datetime64"):
        return "time"
    if lower in VERTICAL_NAMES or standard_name in {"air_pressure", "depth", "height"}:
        return "vertical"
    return None


def detect_coordinates(dataset: xr.Dataset) -> dict[str, str | None]:
    detected = {
        "latitude": None,
        "longitude": None,
        "time": None,
        "vertical": None,
    }
    for name, coord in dataset.coords.items():
        role = _coord_role(name, coord)
        if role and detected[role] is None:
            detected[role] = name
    return detected


def get_coordinate_metadata(dataset: xr.Dataset) -> dict[str, dict[str, Any]]:
    role_map = detect_coordinates(dataset)
    reverse = {name: role for role, name in role_map.items() if name is not None}
    info: dict[str, dict[str, Any]] = {}
    for name, coord in dataset.coords.items():
        entry: dict[str, Any] = {
            "role": reverse.get(name, "dimension"),
            "dtype": str(coord.dtype),
            "attrs": dict(coord.attrs),
            "size": int(coord.size),
        }
        if coord.size:
            first = coord.values[0]
            last = coord.values[-1]
            entry["start"] = str(first)
            entry["end"] = str(last)
        info[name] = entry
    return info
