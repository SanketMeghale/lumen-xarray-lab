from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr

TRANSFORM_OPTIONS = (
    "none",
    "rolling mean",
    "anomaly",
    "resample",
    "climatology",
    "spatial mean",
    "zonal mean",
)
RESAMPLE_RULES = ("MS", "QS-DEC", "YS")
TRANSFORM_AGGREGATIONS = ("mean", "median", "min", "max", "sum")


@dataclass(frozen=True)
class TransformResult:
    array: xr.DataArray
    summary: dict[str, Any]


def _aggregation_function(name: str):
    reducers = {
        "mean": lambda data, dims: data.mean(dim=dims, skipna=True),
        "median": lambda data, dims: data.median(dim=dims, skipna=True),
        "min": lambda data, dims: data.min(dim=dims, skipna=True),
        "max": lambda data, dims: data.max(dim=dims, skipna=True),
        "sum": lambda data, dims: data.sum(dim=dims, skipna=True),
    }
    return reducers.get(name, reducers["mean"])


def _first_matching_dimension(arr: xr.DataArray, coord_name: str | None) -> str | None:
    if coord_name is None or coord_name not in arr.coords:
        return None
    coord = arr.coords[coord_name]
    for dim in coord.dims:
        if dim in arr.dims:
            return dim
    return None


def resolve_time_dimension(arr: xr.DataArray, coord_map: dict[str, str | None]) -> str | None:
    preferred = _first_matching_dimension(arr, coord_map.get("time"))
    if preferred is not None:
        return preferred
    for dim in arr.dims:
        coord = arr.coords.get(dim)
        if coord is not None and pd.api.types.is_datetime64_any_dtype(coord.dtype):
            return dim
    return None


def resolve_spatial_dimensions(arr: xr.DataArray, coord_map: dict[str, str | None]) -> tuple[str | None, str | None]:
    lat_dim = _first_matching_dimension(arr, coord_map.get("latitude"))
    lon_dim = _first_matching_dimension(arr, coord_map.get("longitude"))

    if lat_dim is None:
        for dim in arr.dims:
            if "lat" in dim.lower():
                lat_dim = dim
                break
    if lon_dim is None:
        for dim in arr.dims:
            if "lon" in dim.lower():
                lon_dim = dim
                break
    return lat_dim, lon_dim


def _drop_size_one_dimensions(arr: xr.DataArray) -> xr.DataArray:
    squeeze_dims = [dim for dim in arr.dims if int(arr.sizes.get(dim, 0)) == 1]
    return arr.squeeze(drop=True) if squeeze_dims else arr


def _monthly_anomaly(arr: xr.DataArray, time_dim: str, aggregation: str) -> xr.DataArray:
    if time_dim not in arr.coords or not hasattr(arr[time_dim].dt, "month"):
        return arr - arr.mean(dim=time_dim, skipna=True)
    reducer = _aggregation_function(aggregation)
    climatology = reducer(arr.groupby(f"{time_dim}.month"), time_dim)
    return arr.groupby(f"{time_dim}.month") - climatology


def _monthly_climatology(arr: xr.DataArray, time_dim: str, aggregation: str) -> xr.DataArray:
    reducer = _aggregation_function(aggregation)
    grouped = arr.groupby(f"{time_dim}.month")
    return reducer(grouped, time_dim).rename(month="month")


def apply_transform(
    arr: xr.DataArray,
    coord_map: dict[str, str | None],
    transform: str = "none",
    *,
    window: int = 3,
    aggregation: str = "mean",
    resample_rule: str = "QS-DEC",
) -> TransformResult:
    if transform not in TRANSFORM_OPTIONS:
        raise ValueError(f"Unknown transform {transform!r}.")

    transformed = arr
    summary: dict[str, Any] = {
        "transform": transform,
        "dims_before": list(arr.dims),
        "shape_before": [int(size) for size in arr.shape],
        "aggregation": aggregation,
    }
    time_dim = resolve_time_dimension(arr, coord_map)
    lat_dim, lon_dim = resolve_spatial_dimensions(arr, coord_map)
    summary["time_dim"] = time_dim
    summary["lat_dim"] = lat_dim
    summary["lon_dim"] = lon_dim

    if transform == "rolling mean":
        if time_dim is None:
            raise ValueError("Rolling mean requires a time dimension.")
        transformed = arr.rolling({time_dim: max(int(window), 1)}, min_periods=1).mean()
        summary["window"] = max(int(window), 1)
    elif transform == "anomaly":
        if time_dim is None:
            raise ValueError("Anomaly requires a time dimension.")
        transformed = _monthly_anomaly(arr, time_dim, aggregation)
        summary["baseline"] = "monthly climatology" if time_dim in arr.coords else "overall mean"
    elif transform == "resample":
        if time_dim is None:
            raise ValueError("Resample requires a time dimension.")
        reducer = _aggregation_function(aggregation)
        transformed = reducer(arr.resample({time_dim: resample_rule}), None)
        summary["rule"] = resample_rule
    elif transform == "climatology":
        if time_dim is None:
            raise ValueError("Climatology requires a time dimension.")
        if time_dim not in arr.coords or not hasattr(arr[time_dim].dt, "month"):
            raise ValueError("Climatology requires a datetime coordinate with monthly access.")
        transformed = _monthly_climatology(arr, time_dim, aggregation)
        summary["group"] = "month"
    elif transform == "spatial mean":
        reduce_dims = [dim for dim in (lat_dim, lon_dim) if dim is not None]
        if not reduce_dims:
            raise ValueError("Spatial mean requires detected latitude and longitude dimensions.")
        reducer = _aggregation_function(aggregation)
        transformed = reducer(arr, reduce_dims)
        summary["reduced_dims"] = reduce_dims
    elif transform == "zonal mean":
        if lon_dim is None:
            raise ValueError("Zonal mean requires a detected longitude dimension.")
        reducer = _aggregation_function(aggregation)
        transformed = reducer(arr, [lon_dim])
        summary["reduced_dims"] = [lon_dim]

    transformed = _drop_size_one_dimensions(transformed)
    summary["dims_after"] = list(transformed.dims)
    summary["shape_after"] = [int(size) for size in transformed.shape]
    summary["dtype"] = str(transformed.dtype)
    summary["units"] = transformed.attrs.get("units") or arr.attrs.get("units")
    return TransformResult(array=transformed, summary=summary)

