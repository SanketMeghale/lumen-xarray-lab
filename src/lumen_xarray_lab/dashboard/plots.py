from __future__ import annotations

import pandas as pd
import panel as pn

from .state import DashboardState


def _tabulator(rows: list[dict[str, object]], columns: list[str]) -> pn.viewable.Viewable:
    table = pd.DataFrame(rows, columns=columns)
    return pn.widgets.Tabulator(table, pagination="local", page_size=10, sizing_mode="stretch_width")


def build_preview_table(state: DashboardState) -> pn.viewable.Viewable:
    return pn.widgets.Tabulator(state.preview, pagination="local", page_size=10, sizing_mode="stretch_width")


def build_schema_table(state: DashboardState) -> pn.viewable.Viewable:
    rows = []
    for column, spec in state.schema.items():
        if isinstance(spec, dict):
            rows.append(
                {
                    "column": column,
                    "type": spec.get("type"),
                    "format": spec.get("format"),
                    "description": spec.get("description"),
                    "role": spec.get("role"),
                }
            )
    return _tabulator(rows, ["column", "type", "format", "description", "role"])


def build_dimension_table(state: DashboardState) -> pn.viewable.Viewable:
    rows = []
    for name, spec in state.dimension_info.items():
        rows.append(
            {
                "dimension": name,
                "type": spec.get("type"),
                "dtype": spec.get("dtype"),
                "size": spec.get("size"),
                "min": spec.get("min"),
                "max": spec.get("max"),
            }
        )
    return _tabulator(rows, ["dimension", "type", "dtype", "size", "min", "max"])


def build_coordinate_table(state: DashboardState) -> pn.viewable.Viewable:
    rows = []
    for name, spec in state.coord_metadata.items():
        rows.append(
            {
                "coordinate": name,
                "role": spec.get("role"),
                "dtype": spec.get("dtype"),
                "size": spec.get("size"),
                "start": spec.get("start"),
                "end": spec.get("end"),
            }
        )
    return _tabulator(rows, ["coordinate", "role", "dtype", "size", "start", "end"])


def build_runtime_table(state: DashboardState) -> pn.viewable.Viewable:
    rows = [{"key": key, "value": value} for key, value in state.runtime_details.items()]
    return _tabulator(rows, ["key", "value"])
