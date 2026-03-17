from __future__ import annotations

from pathlib import Path
from typing import Any

import xarray as xr

from .cf import detect_coordinates, get_coordinate_metadata
from .datasets import build_source, get_dataset_from_source

XARRAY_SUFFIXES = (".nc", ".nc4", ".netcdf", ".zarr", ".h5", ".hdf5", ".grib", ".grib2")
ENGINE_MAP = {
    ".nc": "netcdf",
    ".nc4": "netcdf",
    ".netcdf": "netcdf",
    ".zarr": "zarr",
    ".h5": "hdf5",
    ".hdf5": "hdf5",
    ".grib": "grib",
    ".grib2": "grib",
}


def is_xarray_path(path: str) -> bool:
    lowered = path.lower().split("?", 1)[0].split("#", 1)[0]
    return any(lowered.endswith(ext) for ext in XARRAY_SUFFIXES)


def infer_xarray_engine(path: str) -> str | None:
    lowered = path.lower().split("?", 1)[0].split("#", 1)[0]
    for suffix, engine in ENGINE_MAP.items():
        if lowered.endswith(suffix):
            return engine
    return None


def build_ai_context(
    dataset: xr.Dataset,
    table: str | None = None,
    coord_map: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    tables = list(dataset.data_vars)
    active_table = table or (tables[0] if tables else None)
    coord_map = coord_map or detect_coordinates(dataset)
    coord_meta = get_coordinate_metadata(dataset)

    capabilities = ["schema_summary"]
    prompts = ["Summarize the available variables, dimensions, and coordinate roles in this dataset."]

    time_coord = coord_map.get("time")
    lat_coord = coord_map.get("latitude")
    lon_coord = coord_map.get("longitude")
    vertical_coord = coord_map.get("vertical")

    if active_table is not None:
        prompts.append(f"Show the current selection logic for `{active_table}` as a Lumen source query.")

    if time_coord and active_table is not None:
        capabilities.append("time_analysis")
        prompts.append(f"Compute a 12-step rolling mean for `{active_table}` over `{time_coord}`.")
        prompts.append(f"Highlight anomaly periods for `{active_table}` after aggregating non-time dimensions.")

    if lat_coord and lon_coord and active_table is not None:
        capabilities.append("spatial_map")
        prompts.append(f"Render a spatial map for `{active_table}` using `{lat_coord}` and `{lon_coord}`.")

    if vertical_coord and active_table is not None:
        capabilities.append("vertical_profile")
        prompts.append(f"Inspect how `{active_table}` varies across the vertical coordinate `{vertical_coord}`.")

    if len(tables) > 1:
        capabilities.append("compare")
        prompts.append(f"Compare `{tables[0]}` and `{tables[1]}` on their shared coordinates.")

    transform_suggestions = ["rolling mean", "anomaly", "resample", "climatology"]
    if lat_coord and lon_coord:
        transform_suggestions.extend(["spatial mean", "zonal mean"])

    confidence_summary = {
        role: coord_meta[name]["confidence"]
        for role, name in coord_map.items()
        if name is not None and name in coord_meta
    }
    selected_roles = {role: name for role, name in coord_map.items() if name is not None}

    return {
        "table": active_table,
        "tables": tables,
        "capabilities": capabilities,
        "suggested_prompts": prompts,
        "suggested_transforms": transform_suggestions,
        "selected_roles": selected_roles,
        "role_confidence": confidence_summary,
        "dataset_title": str(dataset.attrs.get("title", "Untitled dataset")),
        "table_count": len(tables),
    }


def build_upload_preview(path: str, **source_kwargs: Any) -> dict[str, Any]:
    source = build_source(uri=path, **source_kwargs)
    try:
        tables = source.get_tables()
        table = tables[0] if tables else None
        schema = source.get_schema(table) if table else {}
        dataset = get_dataset_from_source(source)
        coord_map = detect_coordinates(dataset) if dataset is not None else {}
        ai_context = build_ai_context(dataset, table=table, coord_map=coord_map) if dataset is not None else {}
        return {
            "path": path,
            "tables": tables,
            "table": table,
            "schema_keys": list(schema.keys()) if isinstance(schema, dict) else [],
            "detected_coordinates": coord_map,
            "assistant_brief": ai_context,
            "suggested_prompts": ai_context.get("suggested_prompts", []),
            "engine": infer_xarray_engine(path),
            "message": f"Loaded {Path(path).name} with {len(tables)} table(s).",
            "source_backend": type(source).__name__,
        }
    finally:
        if hasattr(source, "close"):
            source.close()


def build_cli_example(path: str) -> str:
    return f"lumen-ai serve {path}"
