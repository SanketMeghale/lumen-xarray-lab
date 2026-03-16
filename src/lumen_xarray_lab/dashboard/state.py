from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import xarray as xr

from ..cf import detect_coordinates, get_coordinate_metadata
from ..datasets import build_source, get_dataset_from_source, resolve_runtime_source_info
from ..schema_enrichment import enrich_schema


def _build_dimension_info_from_dataset(dataset: xr.Dataset, table: str) -> dict[str, Any]:
    arr = dataset[table]
    info: dict[str, Any] = {}
    for dim in arr.dims:
        coord = dataset.coords[dim]
        values = coord.values
        entry: dict[str, Any] = {
            "dtype": str(coord.dtype),
            "size": int(coord.size),
        }
        if pd.api.types.is_datetime64_any_dtype(coord.dtype):
            entry["type"] = "datetime"
            entry["min"] = str(values.min())
            entry["max"] = str(values.max())
        elif pd.api.types.is_numeric_dtype(coord.dtype):
            entry["type"] = "numeric"
            entry["min"] = float(values.min())
            entry["max"] = float(values.max())
        else:
            entry["type"] = "categorical"
            entry["values"] = values.tolist()
        info[dim] = entry
    return info


@dataclass
class DashboardState:
    dataset: xr.Dataset
    source: Any
    tables: list[str]
    table: str
    preview: pd.DataFrame
    schema: dict[str, Any]
    metadata: dict[str, Any]
    dimension_info: dict[str, Any]
    coord_map: dict[str, str | None]
    coord_metadata: dict[str, dict[str, Any]]
    runtime_source: str
    runtime_details: dict[str, Any]

    @classmethod
    def from_dataset(cls, dataset: xr.Dataset, table: str | None = None, **source_kwargs: Any) -> "DashboardState":
        source = build_source(dataset=dataset, **source_kwargs)
        return cls._from_source(source=source, dataset_hint=dataset, table=table)

    @classmethod
    def from_uri(cls, uri: str, table: str | None = None, **source_kwargs: Any) -> "DashboardState":
        source = build_source(uri=uri, **source_kwargs)
        return cls._from_source(source=source, dataset_hint=None, table=table)

    @classmethod
    def _from_source(
        cls,
        source: Any,
        dataset_hint: xr.Dataset | None,
        table: str | None = None,
    ) -> "DashboardState":
        tables = source.get_tables()
        active_table = table or tables[0]
        raw_schema = source.get_schema(active_table)
        metadata = source.get_metadata(active_table)
        source_dataset = get_dataset_from_source(source) or dataset_hint
        if source_dataset is None:
            raise ValueError("Could not resolve an xarray.Dataset from the source.")
        dimension_info = (
            source.get_dimension_info(active_table)
            if hasattr(source, "get_dimension_info")
            else _build_dimension_info_from_dataset(source_dataset, active_table)
        )
        coord_metadata = get_coordinate_metadata(source_dataset)
        schema = enrich_schema(raw_schema, metadata=metadata, coord_info=coord_metadata)
        preview = source.get(active_table).head(25)
        runtime_info = resolve_runtime_source_info()
        return cls(
            dataset=source_dataset,
            source=source,
            tables=tables,
            table=active_table,
            preview=preview,
            schema=schema,
            metadata=metadata,
            dimension_info=dimension_info,
            coord_map=detect_coordinates(source_dataset),
            coord_metadata=coord_metadata,
            runtime_source=runtime_info.backend_label,
            runtime_details=runtime_info.to_dict(),
        )

    def close(self) -> None:
        source_close = getattr(self.source, "close", None)
        if callable(source_close):
            source_close()
