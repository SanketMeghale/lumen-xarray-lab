from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr


@dataclass(frozen=True)
class RuntimeSourceInfo:
    mode: str
    source_class: str
    backend_label: str
    lumen_root: str | None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _desktop_root() -> Path:
    return _repo_root().parent


def _sample_data_root() -> Path:
    return _repo_root() / "assets" / "sample_data"


def _candidate_lumen_paths() -> list[Path]:
    desktop = _desktop_root()
    return [
        desktop / "lumen",
        desktop / "lumen-pr1708",
        desktop / "lumen-xarray-clean",
    ]


def ensure_local_lumen_on_path() -> Path | None:
    for candidate in _candidate_lumen_paths():
        if candidate.exists():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return candidate
    return None


def _normalize_query_value(value: Any) -> Any:
    if isinstance(value, tuple) and len(value) == 2:
        return slice(value[0], value[1])
    return value


def _normalize_scalar_for_coord(coord: xr.DataArray, value: Any) -> Any:
    if np.issubdtype(coord.dtype, np.datetime64):
        if isinstance(value, str):
            return np.datetime64(value)
        if isinstance(value, pd.Timestamp):
            return value.to_datetime64()
    return value


def _dtype_to_schema(dtype: np.dtype) -> dict[str, Any]:
    if np.issubdtype(dtype, np.bool_):
        return {"type": "boolean"}
    if np.issubdtype(dtype, np.integer):
        return {"type": "integer"}
    if np.issubdtype(dtype, np.floating):
        return {"type": "number"}
    if np.issubdtype(dtype, np.datetime64):
        return {"type": "string", "format": "datetime"}
    return {"type": "string"}


def _get_dataframe_schema(df: pd.DataFrame) -> dict[str, Any]:
    schema: dict[str, Any] = {}
    for column in df.columns:
        col = df[column]
        col_schema = _dtype_to_schema(col.dtype)
        non_null = col.dropna()
        if len(non_null) and pd.api.types.is_numeric_dtype(col.dtype):
            col_schema["inclusiveMinimum"] = non_null.min().item()
            col_schema["inclusiveMaximum"] = non_null.max().item()
        elif len(non_null) and pd.api.types.is_datetime64_any_dtype(col.dtype):
            col_schema["inclusiveMinimum"] = str(pd.Timestamp(non_null.min()).to_datetime64())
            col_schema["inclusiveMaximum"] = str(pd.Timestamp(non_null.max()).to_datetime64())
        schema[column] = col_schema
    return schema


@dataclass
class LabXarraySourceAdapter:
    dataset: xr.Dataset | None = None
    uri: str | None = None
    filterable_coords: list[str] | None = None
    max_rows: int = 0
    dataset_format: str = "auto"
    load_kwargs: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.dataset is None and self.uri is None:
            raise ValueError("Provide either 'dataset' or 'uri'.")
        if self.dataset is None:
            self.dataset = self._open_dataset(self.uri)

    def _is_zarr_uri(self, uri: str) -> bool:
        lowered = str(uri).lower()
        return (
            self.dataset_format == "zarr"
            or self.load_kwargs.get("engine") == "zarr"
            or lowered.endswith(".zarr")
        )

    def _open_dataset(self, uri: str | None) -> xr.Dataset:
        if uri is None:
            raise ValueError("A uri is required to open a dataset.")
        if self._is_zarr_uri(uri):
            return xr.open_zarr(uri, **self.load_kwargs)
        return xr.open_dataset(uri, **self.load_kwargs)

    def close(self) -> None:
        if self.dataset is not None and hasattr(self.dataset, "close"):
            self.dataset.close()

    def get_tables(self) -> list[str]:
        assert self.dataset is not None
        return list(self.dataset.data_vars)

    def _get_array(self, table: str) -> xr.DataArray:
        assert self.dataset is not None
        if table not in self.dataset.data_vars:
            raise KeyError(f"Unknown table {table!r}.")
        arr = self.dataset[table]
        return arr if arr.name == table else arr.rename(table)

    def _iter_queryable_coords(self, arr: xr.DataArray) -> list[str]:
        names: list[str] = []
        allowed = set(self.filterable_coords) if self.filterable_coords is not None else None
        for name, coord in arr.coords.items():
            if coord.ndim != 1:
                continue
            if allowed is not None and name not in allowed:
                continue
            names.append(name)
        return names

    def _apply_query(self, arr: xr.DataArray, query: dict[str, Any]) -> xr.DataArray:
        queryable = set(self._iter_queryable_coords(arr))
        for key, raw_value in query.items():
            if key.startswith("__") or key not in queryable:
                continue
            value = _normalize_query_value(raw_value)
            coord = arr.coords[key]
            if isinstance(value, slice):
                arr = arr.sel(
                    {
                        key: slice(
                            _normalize_scalar_for_coord(coord, value.start),
                            _normalize_scalar_for_coord(coord, value.stop),
                            value.step,
                        )
                    }
                )
            elif isinstance(value, list):
                normalized = [_normalize_scalar_for_coord(coord, item) for item in value]
                arr = arr.sel({key: normalized})
            else:
                arr = arr.sel({key: _normalize_scalar_for_coord(coord, value)})
        return arr

    def _to_dataframe(self, arr: xr.DataArray, table: str) -> pd.DataFrame:
        if arr.ndim == 0:
            return pd.DataFrame({table: [arr.item()]})
        df = arr.to_dataframe(name=table).reset_index()
        ordered = [*self._iter_queryable_coords(self._get_array(table)), table]
        df = df[[col for col in ordered if col in df.columns]]
        if self.max_rows and len(df) > self.max_rows:
            raise ValueError(
                f"Query result for table {table!r} produced {len(df)} rows, "
                f"which exceeds max_rows={self.max_rows}."
            )
        return df

    def get(self, table: str, **query: Any) -> pd.DataFrame:
        arr = self._get_array(table)
        arr = self._apply_query(arr, query)
        return self._to_dataframe(arr, table)

    def get_schema(self, table: str | None = None) -> dict[str, Any]:
        tables = [table] if table else self.get_tables()
        schemas: dict[str, Any] = {}
        for name in tables:
            arr = self._get_array(name)
            df = self._to_dataframe(arr, name)
            schema = _get_dataframe_schema(df)
            schema["__len__"] = len(df)
            schemas[name] = schema
        return schemas if table is None else schemas[table]

    def get_metadata(self, table: str | None = None) -> dict[str, Any]:
        tables = [table] if table else self.get_tables()
        metadata: dict[str, Any] = {}
        for name in tables:
            arr = self._get_array(name)
            queryable = self._iter_queryable_coords(arr)
            columns: dict[str, Any] = {}
            for coord_name in queryable:
                coord = arr.coords[coord_name]
                columns[coord_name] = {
                    "description": coord.attrs.get("long_name") or f"{coord_name} coordinate",
                    "data_type": str(coord.dtype),
                }
            columns[name] = {
                "description": arr.attrs.get("long_name") or name,
                "data_type": str(arr.dtype),
            }
            metadata[name] = {
                "description": arr.attrs.get("long_name") or name,
                "dims": list(arr.dims),
                "queryable_coords": queryable,
                "columns": columns,
            }
        return metadata if table is None else metadata[table]

    def get_dimension_info(self, table: str | None = None) -> dict[str, Any]:
        tables = [table] if table else self.get_tables()
        info: dict[str, Any] = {}
        for name in tables:
            arr = self._get_array(name)
            dims: dict[str, Any] = {}
            for coord_name in self._iter_queryable_coords(arr):
                coord = arr.coords[coord_name]
                values = coord.values
                entry: dict[str, Any] = {
                    "dtype": str(coord.dtype),
                    "size": int(coord.size),
                }
                if np.issubdtype(coord.dtype, np.datetime64):
                    entry["type"] = "datetime"
                    entry["min"] = str(values.min())
                    entry["max"] = str(values.max())
                elif np.issubdtype(coord.dtype, np.number):
                    entry["type"] = "numeric"
                    entry["min"] = float(values.min())
                    entry["max"] = float(values.max())
                else:
                    entry["type"] = "categorical"
                    entry["values"] = values.tolist()
                dims[coord_name] = entry
            info[name] = dims
        return info if table is None else info[table]

    def describe(self, table: str | None = None) -> dict[str, Any]:
        tables = [table] if table else self.get_tables()
        return {
            "tables": tables,
            "dimensions": {
                name: self.get_dimension_info(name)
                for name in tables
            },
        }


def resolve_runtime_source_info() -> RuntimeSourceInfo:
    lumen_root = ensure_local_lumen_on_path()
    try:
        from lumen.sources.xarray import XarraySource  # noqa: F401
    except Exception:
        return RuntimeSourceInfo(
            mode="fallback",
            source_class="LabXarraySourceAdapter",
            backend_label="lab-adapter",
            lumen_root=str(lumen_root) if lumen_root else None,
        )
    return RuntimeSourceInfo(
        mode="upstream",
        source_class="XarraySource",
        backend_label="lumen-xarray-source",
        lumen_root=str(lumen_root) if lumen_root else None,
    )


def resolve_runtime_source_name() -> str:
    return resolve_runtime_source_info().backend_label


def build_source(dataset: xr.Dataset | None = None, uri: str | None = None, **kwargs: Any) -> Any:
    ensure_local_lumen_on_path()
    try:
        from lumen.sources.xarray import XarraySource
    except Exception:
        return LabXarraySourceAdapter(dataset=dataset, uri=uri, **kwargs)
    return XarraySource(dataset=dataset, uri=uri, **kwargs)


def get_dataset_from_source(source: Any) -> xr.Dataset | None:
    dataset = getattr(source, "dataset", None)
    if dataset is not None:
        return dataset
    getter = getattr(source, "_get_dataset", None)
    if callable(getter):
        try:
            return getter()
        except Exception:
            return None
    return None


def sample_table_dataframe(
    dataset: xr.Dataset,
    table: str,
    query: dict[str, Any] | None = None,
    limit: int = 250,
    filterable_coords: list[str] | None = None,
) -> pd.DataFrame:
    if table not in dataset.data_vars:
        raise KeyError(f"Unknown table {table!r}.")
    arr = dataset[table]
    allowed = set(filterable_coords) if filterable_coords is not None else None
    queryable = [
        name
        for name, coord in arr.coords.items()
        if coord.ndim == 1 and (allowed is None or name in allowed)
    ]

    for key, raw_value in (query or {}).items():
        if key.startswith("__") or key not in queryable:
            continue
        value = _normalize_query_value(raw_value)
        coord = arr.coords[key]
        if isinstance(value, slice):
            arr = arr.sel(
                {
                    key: slice(
                        _normalize_scalar_for_coord(coord, value.start),
                        _normalize_scalar_for_coord(coord, value.stop),
                        value.step,
                    )
                }
            )
        elif isinstance(value, list):
            normalized = [_normalize_scalar_for_coord(coord, item) for item in value]
            arr = arr.sel({key: normalized})
        else:
            arr = arr.sel({key: _normalize_scalar_for_coord(coord, value)})

    if arr.ndim and any(int(size) == 0 for size in arr.sizes.values()):
        ordered = [*queryable, table]
        return pd.DataFrame(columns=[col for col in ordered if col in ordered])

    if limit > 0 and arr.ndim:
        limited = arr
        dims = list(limited.dims)
        for i, dim in enumerate(dims):
            size = int(limited.sizes[dim])
            trailing = 1
            for tail_dim in dims[i + 1 :]:
                trailing *= int(limited.sizes[tail_dim])
            if trailing == 0:
                limited = limited.isel({dim: slice(0, 0)})
                continue
            max_size = max(1, min(size, int(np.ceil(limit / trailing))))
            if size > max_size:
                limited = limited.isel({dim: slice(0, max_size)})
        arr = limited

    if arr.ndim == 0:
        return pd.DataFrame({table: [arr.item()]})

    df = arr.to_dataframe(name=table).reset_index()
    ordered = [*queryable, table]
    return df[[col for col in ordered if col in df.columns]]


def _build_embedded_demo_dataset() -> xr.Dataset:
    time = np.array(["2013-01-01", "2013-01-02"], dtype="datetime64[ns]")
    lat = np.array([50.0, 60.0])
    lon = np.array([200.0, 210.0])
    air = np.array(
        [
            [[241.2, 242.4], [243.5, 244.7]],
            [[245.2, 246.1], [247.0, 248.3]],
        ]
    )
    ds = xr.Dataset(
        data_vars={
            "air": (("time", "lat", "lon"), air),
        },
        coords={
            "time": time,
            "lat": lat,
            "lon": lon,
        },
        attrs={"title": "Embedded demo dataset"},
    )
    ds["lat"].attrs["units"] = "degrees_north"
    ds["lon"].attrs["units"] = "degrees_east"
    ds["air"].attrs["long_name"] = "Air temperature"
    ds["air"].attrs["units"] = "K"
    return ds


def bundled_sample_paths() -> dict[str, Path]:
    sample_names = ("air_temperature", "compare_weather", "ersstv5", "rasm")
    root = _sample_data_root()
    return {
        name: (root / f"{name}.nc")
        for name in sample_names
        if (root / f"{name}.nc").exists()
    }


def load_demo_dataset(name: str = "air_temperature") -> xr.Dataset:
    local_samples = bundled_sample_paths()
    if name in local_samples:
        return xr.open_dataset(local_samples[name])
    if name == "air_temperature":
        return _build_embedded_demo_dataset()
    try:
        return xr.tutorial.open_dataset(name)
    except Exception:
        return _build_embedded_demo_dataset()


def save_demo_dataset(path: str | Path, name: str = "air_temperature") -> Path:
    dataset = load_demo_dataset(name)
    dataset = dataset.copy(deep=True)
    for variable in dataset.variables:
        dataset[variable].encoding = {}
    target = Path(path)
    dataset.to_netcdf(target)
    dataset.close()
    return target
