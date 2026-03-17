from .ai_hooks import build_ai_context, build_cli_example, build_upload_preview, is_xarray_path
from .benchmark_utils import estimate_dataframe_bytes, estimate_flattened_rows
from .cf import detect_coordinates, get_coordinate_metadata
from .datasets import (
    LabXarraySourceAdapter,
    RuntimeSourceInfo,
    build_source,
    get_dataset_from_source,
    load_demo_dataset,
    resolve_runtime_source_info,
    resolve_runtime_source_name,
)
from .schema_enrichment import enrich_schema
from .sql_source import ExperimentalSQLSource

__all__ = [
    "ExperimentalSQLSource",
    "LabXarraySourceAdapter",
    "RuntimeSourceInfo",
    "build_cli_example",
    "build_ai_context",
    "build_source",
    "build_upload_preview",
    "detect_coordinates",
    "enrich_schema",
    "estimate_dataframe_bytes",
    "estimate_flattened_rows",
    "get_dataset_from_source",
    "get_coordinate_metadata",
    "is_xarray_path",
    "load_demo_dataset",
    "resolve_runtime_source_info",
    "resolve_runtime_source_name",
]
