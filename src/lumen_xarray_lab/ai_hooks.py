from __future__ import annotations

from pathlib import Path
from typing import Any

from .cf import detect_coordinates
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


def build_upload_preview(path: str, **source_kwargs: Any) -> dict[str, Any]:
    source = build_source(uri=path, **source_kwargs)
    try:
        tables = source.get_tables()
        table = tables[0] if tables else None
        schema = source.get_schema(table) if table else {}
        dataset = get_dataset_from_source(source)
        coord_map = detect_coordinates(dataset) if dataset is not None else {}
        return {
            "path": path,
            "tables": tables,
            "table": table,
            "schema_keys": list(schema.keys()) if isinstance(schema, dict) else [],
            "detected_coordinates": coord_map,
            "engine": infer_xarray_engine(path),
            "message": f"Loaded {Path(path).name} with {len(tables)} table(s).",
            "source_backend": type(source).__name__,
        }
    finally:
        if hasattr(source, "close"):
            source.close()


def build_cli_example(path: str) -> str:
    return f"lumen-ai serve {path}"
