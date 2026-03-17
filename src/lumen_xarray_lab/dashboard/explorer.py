from __future__ import annotations

import json
from html import escape
from io import StringIO
from typing import Any

import numpy as np
import pandas as pd
import panel as pn
import param

from bokeh.models import BasicTicker, ColorBar, ColumnDataSource, HoverTool, LinearColorMapper
from bokeh.palettes import Blues256
from bokeh.plotting import figure
from panel.viewable import Viewer

from ..datasets import apply_query_to_array, estimate_query_cost, sample_table_dataframe
from .state import DashboardState

ROLE_ORDER = ("time", "latitude", "longitude", "vertical")
_SPATIAL_FALLBACKS = {
    "latitude": ["lat", "latitude", "y"],
    "longitude": ["lon", "longitude", "x"],
}


def _dimension_info_for_table(state: DashboardState, table: str) -> dict[str, Any]:
    arr = state.dataset[table]
    info: dict[str, Any] = {}
    for dim in arr.dims:
        coord = state.dataset.coords[dim]
        values = coord.values
        entry: dict[str, Any] = {
            "dtype": str(coord.dtype),
            "size": int(coord.size),
            "values": values,
        }
        if pd.api.types.is_datetime64_any_dtype(coord.dtype):
            entry["type"] = "datetime"
        elif pd.api.types.is_numeric_dtype(coord.dtype):
            entry["type"] = "numeric"
        else:
            entry["type"] = "categorical"
        info[dim] = entry
    return info


def _format_scalar(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.datetime64):
        return str(pd.Timestamp(value))
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _resolve_role_column(state: DashboardState, df: pd.DataFrame, role: str) -> str | None:
    preferred = state.coord_map.get(role)
    if preferred in df.columns:
        return preferred
    for candidate in _SPATIAL_FALLBACKS.get(role, []):
        if candidate in df.columns:
            return candidate
    return None


class ExplorerView(Viewer):
    state = param.Parameter()

    def __init__(self, **params: Any):
        super().__init__(**params)
        self._filter_widgets: dict[str, pn.widgets.Widget] = {}

        self._table_search = pn.widgets.AutocompleteInput(
            name="Search table",
            options=self.state.tables,
            value=self.state.table,
            restrict=True,
            case_sensitive=False,
            search_strategy="includes",
            min_characters=0,
            placeholder="Search or select a table...",
            sizing_mode="stretch_width",
        )
        self._table = pn.widgets.Select(name="Active table", options=self.state.tables, value=self.state.table)
        self._chart_type = pn.widgets.Select(
            name="Chart",
            options=["line", "scatter", "bar", "histogram", "spatial"],
            value="line",
        )
        self._x = pn.widgets.Select(name="X axis", options=[])
        self._y = pn.widgets.Select(name="Y axis", options=[])
        self._limit = pn.widgets.IntSlider(name="Row limit", start=25, end=1000, step=25, value=250)
        self._plot_resolution = pn.widgets.IntSlider(name="Plot resolution", start=25, end=400, step=25, value=150)
        self._spatial_resolution = pn.widgets.IntSlider(name="Spatial bins", start=8, end=48, step=4, value=24)
        self._compare_table = pn.widgets.Select(name="Compare table", options=["None"], value="None")
        self._compare_mode = pn.widgets.Select(name="Compare mode", options=["difference", "ratio"], value="difference")
        self._time_mode = pn.widgets.Select(
            name="Analysis mode",
            options=["raw", "rolling mean", "anomaly", "cumulative", "trend"],
            value="raw",
        )
        self._time_agg = pn.widgets.Select(
            name="Aggregate across other dims",
            options=["mean", "median", "min", "max"],
            value="mean",
        )
        self._time_window = pn.widgets.IntSlider(name="Rolling window", start=2, end=24, step=1, value=5)

        self._filters = pn.Column(sizing_mode="stretch_width")
        self._query = pn.pane.Markdown(sizing_mode="stretch_width", css_classes=["lxl-card-markdown"])
        self._sql = pn.pane.Markdown(sizing_mode="stretch_width", css_classes=["lxl-card-markdown"])
        self._chart = pn.Column(sizing_mode="stretch_width", min_height=420)
        self._time_plot = pn.Column(sizing_mode="stretch_width", min_height=420)
        self._data = pn.widgets.Tabulator(pd.DataFrame(), pagination="local", page_size=12, sizing_mode="stretch_width")
        self._stats = pn.widgets.Tabulator(pd.DataFrame(), pagination="local", page_size=10, sizing_mode="stretch_width")
        self._coverage_table = pn.widgets.Tabulator(pd.DataFrame(), pagination="local", page_size=10, sizing_mode="stretch_width")
        self._compare_table_view = pn.widgets.Tabulator(pd.DataFrame(), pagination="local", page_size=10, sizing_mode="stretch_width")
        self._cf_table = pn.widgets.Tabulator(pd.DataFrame(), pagination="local", page_size=6, sizing_mode="stretch_width")
        self._coverage_summary = pn.pane.Markdown(css_classes=["lxl-card-markdown"])
        self._compare_summary = pn.pane.Markdown(css_classes=["lxl-card-markdown"])
        self._time_summary = pn.pane.Markdown(css_classes=["lxl-card-markdown"])
        self._status = pn.pane.Markdown(css_classes=["lxl-card-markdown"])
        self._summary = pn.pane.HTML(sizing_mode="stretch_width")
        self._selection_banner = pn.pane.HTML(sizing_mode="stretch_width")
        self._field_inventory = pn.pane.HTML(sizing_mode="stretch_width")
        self._active_filters = pn.pane.Markdown(css_classes=["lxl-card-markdown"])
        self._dataset_info = pn.pane.HTML(sizing_mode="stretch_width")
        self._attribute_preview = pn.pane.Markdown(css_classes=["lxl-card-markdown"])
        self._query_cost = pn.pane.HTML(sizing_mode="stretch_width")
        self._query_warning = pn.pane.Markdown(css_classes=["lxl-card-markdown"])
        self._download_csv = pn.widgets.FileDownload(
            label="Current CSV",
            button_type="primary",
            callback=self._export_csv,
            filename="selection.csv",
            sizing_mode="stretch_width",
        )
        self._download_json = pn.widgets.FileDownload(
            label="Current JSON",
            button_type="light",
            callback=self._export_json,
            filename="selection.json",
            sizing_mode="stretch_width",
        )

        self._table_search.param.watch(self._on_table_search, "value")
        self._table.param.watch(self._on_table_change, "value")
        for widget in (
            self._chart_type,
            self._x,
            self._y,
            self._limit,
            self._plot_resolution,
            self._spatial_resolution,
            self._compare_table,
            self._compare_mode,
            self._time_mode,
            self._time_agg,
            self._time_window,
        ):
            widget.param.watch(self._update_outputs, "value")

        self._rebuild_filters()
        self._sync_axis_options()
        self._sync_compare_options()
        self._update_outputs()

        paper_styles = {
            "border-radius": "12px",
            "box-shadow": "0 1px 2px rgba(15, 23, 42, 0.06), 0 8px 24px rgba(15, 23, 42, 0.06)",
            "background": "#ffffff",
            "border": "1px solid #d9e1ea",
        }

        dataset_card = pn.Card(
            pn.Column(
                pn.pane.HTML("<div class='lxl-explorer-section-title'>Dataset</div>"),
                self._table_search,
                self._table,
                self._field_inventory,
                sizing_mode="stretch_width",
            ),
            title="Select Data to Explore",
            collapsed=False,
            sizing_mode="stretch_width",
            css_classes=["lxl-paper-card", "lxl-explorer-dataset-card"],
            styles=paper_styles,
        )
        dataset_info_card = pn.Card(
            pn.Column(
                self._dataset_info,
                pn.pane.HTML("<div class='lxl-explorer-section-title'>CF Metadata</div>"),
                self._cf_table,
                pn.pane.HTML("<div class='lxl-explorer-section-title'>Attribute Preview</div>"),
                self._attribute_preview,
                sizing_mode="stretch_width",
            ),
            title="Dataset Info / CF Metadata",
            collapsed=False,
            sizing_mode="stretch_width",
            css_classes=["lxl-paper-card", "lxl-explorer-dataset-info-card"],
            styles=paper_styles,
        )
        visual_card = pn.Card(
            pn.Column(
                pn.pane.HTML("<div class='lxl-explorer-section-title'>Visual Controls</div>"),
                self._chart_type,
                self._x,
                self._y,
                self._limit,
                self._plot_resolution,
                self._spatial_resolution,
                sizing_mode="stretch_width",
            ),
            title="Visualization",
            collapsed=False,
            sizing_mode="stretch_width",
            css_classes=["lxl-paper-card", "lxl-explorer-visual-card"],
            styles=paper_styles,
        )
        query_card = pn.Card(
            pn.Column(
                pn.pane.HTML("<div class='lxl-explorer-section-title'>Query Cost</div>"),
                self._query_cost,
                self._query_warning,
                sizing_mode="stretch_width",
            ),
            title="Query Planning",
            collapsed=False,
            sizing_mode="stretch_width",
            css_classes=["lxl-paper-card", "lxl-explorer-query-card"],
            styles=paper_styles,
        )
        filter_card = pn.Card(
            pn.Column(
                pn.pane.HTML("<div class='lxl-explorer-section-title'>Active Query</div>"),
                self._active_filters,
                pn.pane.HTML("<div class='lxl-explorer-section-title'>Dimension Filters</div>"),
                self._filters,
                sizing_mode="stretch_width",
            ),
            title="Filters",
            collapsed=False,
            sizing_mode="stretch_width",
            css_classes=["lxl-paper-card", "lxl-explorer-filter-card"],
            styles=paper_styles,
        )
        compare_card = pn.Card(
            pn.Column(
                pn.pane.HTML("<div class='lxl-explorer-section-title'>Compare / Export</div>"),
                self._compare_table,
                self._compare_mode,
                pn.Row(self._download_csv, self._download_json, sizing_mode="stretch_width"),
                self._status,
                sizing_mode="stretch_width",
            ),
            title="Actions",
            collapsed=False,
            sizing_mode="stretch_width",
            css_classes=["lxl-paper-card", "lxl-explorer-action-card"],
            styles=paper_styles,
        )

        self._output_tabs = pn.Tabs(
            ("Chart", self._chart),
            ("Data", self._data),
            ("Statistics", self._stats),
            (
                "Time Analysis",
                pn.Column(
                    pn.Row(self._time_mode, self._time_agg, self._time_window, sizing_mode="stretch_width"),
                    self._time_summary,
                    self._time_plot,
                    sizing_mode="stretch_width",
                ),
            ),
            ("Compare", pn.Column(self._compare_summary, self._compare_table_view, sizing_mode="stretch_width")),
            ("Coverage", pn.Column(self._coverage_summary, self._coverage_table, sizing_mode="stretch_width")),
            ("Source Query", self._query),
            ("Pseudo SQL", self._sql),
            sizing_mode="stretch_width",
        )

        self._selection_card = pn.Card(
            self._summary,
            title="Selection Summary",
            collapsed=False,
            sizing_mode="stretch_width",
            css_classes=["lxl-paper-card", "lxl-explorer-selection-card"],
            styles=paper_styles,
        )
        self._output_card = pn.Card(
            self._output_tabs,
            title="Explorer Output",
            collapsed=False,
            sizing_mode="stretch_width",
            css_classes=["lxl-paper-card", "lxl-explorer-output-card"],
            styles=paper_styles,
        )

        self._layout = pn.Row(
            pn.Column(
                dataset_card,
                dataset_info_card,
                visual_card,
                query_card,
                filter_card,
                compare_card,
                min_width=360,
                max_width=390,
                sizing_mode="stretch_height",
                css_classes=["lxl-explorer-rail"],
            ),
            pn.Column(
                self._selection_banner,
                pn.Row(
                    self._selection_card,
                    sizing_mode="stretch_width",
                ),
                self._output_card,
                sizing_mode="stretch_width",
            ),
            sizing_mode="stretch_width",
            css_classes=["lxl-explorer-root"],
        )

    @property
    def filter_widgets(self) -> dict[str, pn.widgets.Widget]:
        return self._filter_widgets

    def _queryable_columns(self, table: str) -> list[str]:
        arr = self.state.dataset[table]
        allowed = getattr(self.state.source, "filterable_coords", None)
        allowed_set = set(allowed) if allowed is not None else None
        return [
            name
            for name, coord in arr.coords.items()
            if coord.ndim == 1 and (allowed_set is None or name in allowed_set)
        ]

    def _table_columns(self, table: str) -> list[str]:
        return [*self._queryable_columns(table), table]

    def _numeric_columns(self, table: str) -> list[str]:
        arr = self.state.dataset[table]
        numeric = [
            name
            for name in self._queryable_columns(table)
            if pd.api.types.is_numeric_dtype(arr.coords[name].dtype)
        ]
        if pd.api.types.is_numeric_dtype(arr.dtype):
            numeric.append(table)
        return numeric

    def _default_filter_value(self, spec: dict[str, Any]) -> Any:
        if spec["type"] == "datetime":
            values = pd.to_datetime(spec["values"])
            return (values.min().to_pydatetime(), values.max().to_pydatetime())
        if spec["type"] == "numeric":
            values = np.asarray(spec["values"], dtype=float)
            return (float(np.min(values)), float(np.max(values)))
        return "All"

    def _ordered_dimensions(self, table: str) -> list[tuple[str, dict[str, Any]]]:
        dim_info = _dimension_info_for_table(self.state, table)
        role_rank = {
            coord_name: index
            for index, role in enumerate(ROLE_ORDER)
            if (coord_name := self.state.coord_map.get(role)) is not None
        }
        return sorted(dim_info.items(), key=lambda item: (role_rank.get(item[0], len(ROLE_ORDER)), item[0]))

    def _rebuild_filters(self) -> None:
        self._filter_widgets.clear()
        self._filters.objects = []
        widgets: list[pn.viewable.Viewable] = []

        for name, spec in self._ordered_dimensions(self._table.value):
            widget: pn.widgets.Widget
            if spec["type"] == "datetime":
                values = pd.to_datetime(spec["values"])
                start = values.min().to_pydatetime()
                end = values.max().to_pydatetime()
                widget = pn.widgets.DatetimeRangeSlider(
                    name=name,
                    start=start,
                    end=end,
                    value=(start, end),
                )
            elif spec["type"] == "numeric":
                values = np.asarray(spec["values"], dtype=float)
                start = float(np.min(values))
                end = float(np.max(values))
                widget = pn.widgets.RangeSlider(
                    name=name,
                    start=start,
                    end=end,
                    value=(start, end),
                    step=(end - start) / max(spec["size"] - 1, 1) if start != end else 1.0,
                )
            else:
                values = ["All", *[str(value) for value in spec["values"]]]
                widget = pn.widgets.Select(name=name, options=values, value="All")
            widget.param.watch(self._update_outputs, "value")
            self._filter_widgets[name] = widget
            widgets.append(widget)

        self._filters.objects = widgets

    def _preferred_x_column(self, columns: list[str], default_y: str) -> str:
        preferred = [
            self.state.coord_map.get("time"),
            self.state.coord_map.get("longitude"),
            self.state.coord_map.get("latitude"),
            self.state.coord_map.get("vertical"),
        ]
        for candidate in preferred:
            if candidate in columns and candidate != default_y:
                return candidate
        return next((col for col in columns if col != default_y), columns[0])

    def _sync_axis_options(self) -> None:
        columns = self._table_columns(self._table.value)
        numeric = self._numeric_columns(self._table.value)
        default_y = self._table.value if self._table.value in numeric else (numeric[0] if numeric else columns[-1])
        default_x = self._preferred_x_column(columns, default_y)
        self._x.options = columns
        self._y.options = numeric or columns
        self._x.value = default_x
        self._y.value = default_y

    def _sync_compare_options(self) -> None:
        options = ["None", *[table for table in self.state.tables if table != self._table.value]]
        self._compare_table.options = options
        if self._compare_table.value not in options:
            self._compare_table.value = "None"
        self._compare_mode.disabled = self._compare_table.value == "None"

    def _active_filter_lines(self) -> list[str]:
        filters = self._collect_query()
        lines = ["**Active filters**"]
        if not filters:
            lines.append("- none")
        else:
            for key, value in filters.items():
                if isinstance(value, tuple) and len(value) == 2:
                    lines.append(f"- `{key}` between `{value[0]}` and `{value[1]}`")
                else:
                    lines.append(f"- `{key}` = `{value}`")
        if self._compare_table.value != "None":
            lines.append(f"- compare `{self._table.value}` vs `{self._compare_table.value}` as `{self._compare_mode.value}`")
        return lines

    def _collect_query(self) -> dict[str, Any]:
        query: dict[str, Any] = {}
        dim_info = _dimension_info_for_table(self.state, self._table.value)
        for name, widget in self._filter_widgets.items():
            value = widget.value
            if isinstance(widget, pn.widgets.Select):
                if value != "All":
                    query[name] = value
            else:
                spec = dim_info[name]
                current = tuple(value)
                full = self._default_filter_value(spec)
                if current != full:
                    query[name] = current
        return query

    def _table_row_count(self, table: str) -> int:
        schema = self.state.source.get_schema(table)
        if isinstance(schema, dict):
            value = schema.get("__len__", 0)
            return int(value) if value is not None else 0
        return 0

    def _current_array(self):
        return apply_query_to_array(
            self.state.dataset[self._table.value],
            query=self._collect_query(),
            filterable_coords=getattr(self.state.source, "filterable_coords", None),
        )

    def current_query_cost(self) -> dict[str, Any]:
        return estimate_query_cost(
            self.state.dataset,
            self._table.value,
            query=self._collect_query(),
            filterable_coords=getattr(self.state.source, "filterable_coords", None),
        )

    def _downsample_frame(self, df: pd.DataFrame, order_by: str | None = None) -> pd.DataFrame:
        if df.empty:
            return df
        resolution = max(int(self._plot_resolution.value), 1)
        ordered = df.sort_values(order_by) if order_by and order_by in df.columns else df
        if len(ordered) <= resolution:
            return ordered
        indices = np.linspace(0, len(ordered) - 1, resolution, dtype=int)
        return ordered.iloc[np.unique(indices)]

    def _aggregate_spatial_dataframe(self, df: pd.DataFrame, lat_col: str, lon_col: str, value_col: str) -> pd.DataFrame:
        spatial = df.copy()
        spatial["__lon__"] = pd.to_numeric(spatial[lon_col], errors="coerce")
        spatial["__lat__"] = pd.to_numeric(spatial[lat_col], errors="coerce")
        spatial["__value__"] = pd.to_numeric(spatial[value_col], errors="coerce")
        spatial = spatial.dropna(subset=["__lon__", "__lat__", "__value__"])
        if spatial.empty:
            return spatial

        bins = max(int(self._spatial_resolution.value), 4)
        lat_unique = int(spatial["__lat__"].nunique())
        lon_unique = int(spatial["__lon__"].nunique())
        if len(spatial) <= bins * bins or (lat_unique <= bins and lon_unique <= bins):
            return spatial

        lat_bins = min(bins, max(lat_unique, 1))
        lon_bins = min(bins, max(lon_unique, 1))
        spatial["__lat_bin__"] = pd.cut(spatial["__lat__"], bins=lat_bins, duplicates="drop")
        spatial["__lon_bin__"] = pd.cut(spatial["__lon__"], bins=lon_bins, duplicates="drop")
        grouped = (
            spatial.groupby(["__lat_bin__", "__lon_bin__"], observed=True)["__value__"]
            .mean()
            .reset_index()
        )
        grouped["__lat__"] = grouped["__lat_bin__"].apply(lambda interval: float(interval.mid) if pd.notna(interval) else np.nan)
        grouped["__lon__"] = grouped["__lon_bin__"].apply(lambda interval: float(interval.mid) if pd.notna(interval) else np.nan)
        return grouped.dropna(subset=["__lat__", "__lon__", "__value__"])

    def _time_dimension(self) -> str | None:
        preferred = self.state.coord_map.get("time")
        arr = self.state.dataset[self._table.value]
        if preferred in arr.dims:
            return preferred
        for dim in arr.dims:
            coord = arr.coords.get(dim)
            if coord is not None and pd.api.types.is_datetime64_any_dtype(coord.dtype):
                return dim
        return None

    def _time_analysis_frame(self) -> tuple[pd.DataFrame, dict[str, Any]]:
        time_dim = self._time_dimension()
        if time_dim is None:
            return pd.DataFrame(), {"error": "No time dimension is available for the active table."}

        arr = self._current_array()
        if time_dim not in arr.dims:
            return pd.DataFrame(), {"error": f"Detected time coordinate `{time_dim}` is not a dimension on the active table."}

        reducer = {
            "mean": lambda data, dims: data.mean(dim=dims, skipna=True),
            "median": lambda data, dims: data.median(dim=dims, skipna=True),
            "min": lambda data, dims: data.min(dim=dims, skipna=True),
            "max": lambda data, dims: data.max(dim=dims, skipna=True),
        }
        reduce_dims = [dim for dim in arr.dims if dim != time_dim]
        reduced = reducer[self._time_agg.value](arr, reduce_dims) if reduce_dims else arr
        series = reduced.to_series()
        if isinstance(series.index, pd.MultiIndex):
            series = series.groupby(level=0).mean()
        series = pd.to_numeric(series, errors="coerce").dropna().sort_index()
        if series.empty:
            return pd.DataFrame(), {"error": "Time analysis produced an empty series for the current selection."}

        frame = pd.DataFrame({"time": pd.to_datetime(series.index), "raw": series.to_numpy(dtype=float)})
        mode = self._time_mode.value
        frame["value"] = frame["raw"]
        trend_slope = None
        trend_line = None

        if mode == "rolling mean":
            frame["value"] = frame["raw"].rolling(self._time_window.value, min_periods=1).mean()
        elif mode == "anomaly":
            frame["value"] = frame["raw"] - frame["raw"].mean()
        elif mode == "cumulative":
            frame["value"] = frame["raw"].cumsum()
        elif mode == "trend":
            if len(frame) > 1:
                idx = np.arange(len(frame), dtype=float)
                trend_slope, intercept = np.polyfit(idx, frame["raw"], 1)
                trend_line = intercept + trend_slope * idx
                frame["trend"] = trend_line
            else:
                frame["trend"] = frame["raw"]

        frame = self._downsample_frame(frame, order_by="time")
        return frame, {
            "time_dim": time_dim,
            "mode": mode,
            "aggregation": self._time_agg.value,
            "points": int(len(series)),
            "start": _format_scalar(frame["time"].min()) if not frame.empty else "n/a",
            "end": _format_scalar(frame["time"].max()) if not frame.empty else "n/a",
            "mean": float(series.mean()),
            "std": float(series.std()) if len(series) > 1 else 0.0,
            "trend_slope": trend_slope,
        }

    def _build_time_analysis_output(self) -> tuple[str, pn.viewable.Viewable]:
        frame, summary = self._time_analysis_frame()
        if "error" in summary:
            return summary["error"], pn.pane.Markdown(summary["error"])

        lines = [
            f"**Time dimension:** `{summary['time_dim']}`",
            f"**Aggregation:** `{summary['aggregation']}`",
            f"**Mode:** `{summary['mode']}`",
            f"**Points:** {summary['points']}",
            f"**Range:** `{summary['start']}` -> `{summary['end']}`",
            f"**Mean:** {summary['mean']:.4f}",
            f"**Std:** {summary['std']:.4f}",
            f"**Resolution:** {self._plot_resolution.value} plotted points max",
        ]
        if summary["mode"] == "rolling mean":
            lines.append(f"**Rolling window:** {self._time_window.value}")
        if summary["mode"] == "trend" and summary["trend_slope"] is not None:
            lines.append(f"**Trend slope / step:** {summary['trend_slope']:.6f}")

        plot = figure(
            height=380,
            sizing_mode="stretch_width",
            title=f"Time analysis: {self._table.value}",
            x_axis_type="datetime",
        )
        source = ColumnDataSource(frame.assign(__time__=frame["time"], __value__=frame["value"], __raw__=frame["raw"]))
        plot.line("__time__", "__value__", line_width=3, color="#1976d2", source=source)
        plot.scatter("__time__", "__value__", size=6, color="#64b5f6", line_color="#1565c0", source=source)
        if "trend" in frame.columns:
            trend_source = ColumnDataSource(frame.assign(__time__=frame["time"], __trend__=frame["trend"]))
            plot.line("__time__", "__trend__", line_width=2.5, color="#ef6c00", line_dash="dashed", source=trend_source)
        plot.add_tools(HoverTool(tooltips=[("time", "@__time__{%F}"), ("value", "@__value__{0.000}")], formatters={"@__time__": "datetime"}))
        self._style_plot(plot)
        return "\n".join(lines), plot

    def _build_dataset_info_html(self) -> str:
        arr = self.state.dataset[self._table.value]
        table_meta = self.state.metadata if isinstance(self.state.metadata, dict) else {}
        dataset_title = escape(str(self.state.dataset.attrs.get("title", "Untitled dataset")))
        description = escape(str(table_meta.get("description") or arr.attrs.get("long_name") or "No description"))
        dims = ", ".join(f"{dim}:{int(arr.sizes[dim])}" for dim in arr.dims) or "scalar"
        units = escape(str(arr.attrs.get("units") or table_meta.get("columns", {}).get(self._table.value, {}).get("unit") or "n/a"))
        standard_name = escape(str(arr.attrs.get("standard_name", "n/a")))
        roles = ", ".join(f"{role}={name}" for role, name in self.state.coord_map.items() if name) or "none"
        full_cost = estimate_query_cost(
            self.state.dataset,
            self._table.value,
            filterable_coords=getattr(self.state.source, "filterable_coords", None),
        )
        return (
            "<div class='lxl-info-grid'>"
            f"<div><span class='lxl-explorer-label'>Dataset</span><strong>{dataset_title}</strong><em>{description}</em></div>"
            f"<div><span class='lxl-explorer-label'>Table</span><strong>{escape(self._table.value)}</strong><em>dims: {escape(dims)}</em></div>"
            f"<div><span class='lxl-explorer-label'>Units</span><strong>{units}</strong><em>standard_name: {standard_name}</em></div>"
            f"<div><span class='lxl-explorer-label'>Queryable coords</span><strong>{escape(', '.join(table_meta.get('queryable_coords', [])) or 'none')}</strong><em>roles: {escape(roles)}</em></div>"
            f"<div><span class='lxl-explorer-label'>Full flatten rows</span><strong>{full_cost['full_rows']:,}</strong><em>approx {full_cost['approx_dataframe_mb']:.2f} MB if fully materialized</em></div>"
            f"<div><span class='lxl-explorer-label'>Runtime</span><strong>{escape(self.state.runtime_source)}</strong><em>{escape(str(self.state.runtime_details.get('source_class', 'unknown')))}</em></div>"
            "</div>"
        )

    def _build_cf_dataframe(self) -> pd.DataFrame:
        rows = []
        for name, spec in self.state.coord_metadata.items():
            rows.append(
                {
                    "coordinate": name,
                    "selected_role": spec.get("selected_role") or spec.get("role"),
                    "confidence": spec.get("confidence"),
                    "units": spec.get("units"),
                    "standard_name": spec.get("standard_name"),
                    "axis": spec.get("axis"),
                    "dtype": spec.get("dtype"),
                    "size": spec.get("size"),
                }
            )
        return pd.DataFrame(rows)

    def _build_attribute_preview(self) -> str:
        payload = {
            "dataset_attrs": dict(self.state.dataset.attrs),
            "table_attrs": dict(self.state.dataset[self._table.value].attrs),
        }
        return f"```json\n{json.dumps(payload, indent=2, default=str)}\n```"

    def _build_query_cost_html(self, cost: dict[str, Any], sampled_rows: int) -> str:
        risk = cost["risk"]
        return (
            "<div class='lxl-cost-grid'>"
            f"<div><span class='lxl-explorer-label'>Estimated rows</span><strong>{cost['selected_rows']:,}</strong><em>before preview sampling</em></div>"
            f"<div><span class='lxl-explorer-label'>Approx. frame size</span><strong>{cost['approx_dataframe_mb']:.2f} MB</strong><em>{cost['column_count']} output columns</em></div>"
            f"<div><span class='lxl-explorer-label'>Selection ratio</span><strong>{cost['selection_ratio'] * 100:.2f}%</strong><em>of {cost['full_rows']:,} table rows</em></div>"
            f"<div><span class='lxl-explorer-label'>Preview rows</span><strong>{sampled_rows}</strong><em>row limit: {self._limit.value}</em></div>"
            f"<div><span class='lxl-explorer-label'>Risk</span><strong><span class='lxl-risk-chip lxl-risk-{risk}'>{risk}</span></strong><em>flattening cost estimate</em></div>"
            f"<div><span class='lxl-explorer-label'>Resolution</span><strong>{self._plot_resolution.value} / {self._spatial_resolution.value}</strong><em>plot points / spatial bins</em></div>"
            "</div>"
        )

    def current_dataframe(self) -> pd.DataFrame:
        return sample_table_dataframe(
            self.state.dataset,
            self._table.value,
            query=self._collect_query(),
            limit=self._limit.value,
            filterable_coords=getattr(self.state.source, "filterable_coords", None),
        )

    def source_query_text(self) -> str:
        parts = [repr(self._table.value)]
        for key, value in self._collect_query().items():
            parts.append(f"{key}={value!r}")
        return f"source.get({', '.join(parts)})"

    def sql_preview_text(self) -> str:
        where = []
        for key, value in self._collect_query().items():
            if isinstance(value, tuple) and len(value) == 2:
                where.append(f"{key} BETWEEN {value[0]!r} AND {value[1]!r}")
            else:
                where.append(f"{key} = {value!r}")
        clause = f" WHERE {' AND '.join(where)}" if where else ""
        return f'SELECT * FROM "{self._table.value}"{clause} LIMIT {self._limit.value}'

    def _build_statistics_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for column in df.columns:
            series = df[column]
            entry: dict[str, Any] = {
                "column": column,
                "dtype": str(series.dtype),
                "non_null": int(series.notna().sum()),
                "missing": int(series.isna().sum()),
                "unique": int(series.nunique(dropna=True)),
            }
            if pd.api.types.is_numeric_dtype(series):
                numeric = pd.to_numeric(series, errors="coerce")
                entry.update(
                    {
                        "min": float(numeric.min()) if numeric.notna().any() else np.nan,
                        "mean": float(numeric.mean()) if numeric.notna().any() else np.nan,
                        "max": float(numeric.max()) if numeric.notna().any() else np.nan,
                        "std": float(numeric.std()) if numeric.notna().sum() > 1 else np.nan,
                    }
                )
            elif pd.api.types.is_datetime64_any_dtype(series):
                non_null = pd.to_datetime(series.dropna())
                entry.update(
                    {
                        "min": _format_scalar(non_null.min()) if not non_null.empty else "n/a",
                        "mean": "n/a",
                        "max": _format_scalar(non_null.max()) if not non_null.empty else "n/a",
                        "std": "n/a",
                    }
                )
            else:
                mode = series.mode(dropna=True)
                entry.update(
                    {
                        "min": mode.iloc[0] if not mode.empty else "n/a",
                        "mean": "n/a",
                        "max": "n/a",
                        "std": "n/a",
                    }
                )
            rows.append(entry)
        return pd.DataFrame(rows)

    def _build_coverage_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        dim_info = _dimension_info_for_table(self.state, self._table.value)
        rows: list[dict[str, Any]] = []
        for name, spec in dim_info.items():
            if name in df.columns and not df.empty:
                selected = df[name]
                unique_selected = int(selected.nunique(dropna=True))
                minimum = _format_scalar(selected.min())
                maximum = _format_scalar(selected.max())
            else:
                unique_selected = 0
                minimum = "n/a"
                maximum = "n/a"
            total_unique = int(spec["size"])
            rows.append(
                {
                    "dimension": name,
                    "dtype": spec["dtype"],
                    "selected_unique": unique_selected,
                    "total_unique": total_unique,
                    "selected_pct": round((unique_selected / total_unique) * 100, 1) if total_unique else 0.0,
                    "min": minimum,
                    "max": maximum,
                }
            )
        return pd.DataFrame(rows)

    def _build_comparison_dataframe(self, current_df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
        other_table = self._compare_table.value
        if other_table == "None":
            return "Select another table to compare on shared coordinates.", pd.DataFrame()

        try:
            other_df = sample_table_dataframe(
                self.state.dataset,
                other_table,
                query=self._collect_query(),
                limit=self._limit.value,
                filterable_coords=getattr(self.state.source, "filterable_coords", None),
            )
        except Exception as exc:  # pragma: no cover - defensive UI path
            return f"Comparison query failed for `{other_table}`: {exc}", pd.DataFrame()

        join_keys = [col for col in current_df.columns if col in other_df.columns and col not in {self._table.value, other_table}]
        if not join_keys:
            return f"No shared coordinates found between `{self._table.value}` and `{other_table}`.", pd.DataFrame()

        merged = current_df.merge(other_df, on=join_keys, how="inner")
        primary = pd.to_numeric(merged[self._table.value], errors="coerce")
        secondary = pd.to_numeric(merged[other_table], errors="coerce")
        merged["difference"] = primary - secondary
        denominator = secondary.replace(0, np.nan)
        merged["ratio"] = primary / denominator

        mode = self._compare_mode.value
        focus_col = "difference" if mode == "difference" else "ratio"
        correlation = primary.corr(secondary)
        summary = "\n".join(
            [
                f"**Compare:** `{self._table.value}` vs `{other_table}`",
                f"**Join keys:** {', '.join(join_keys)}",
                f"**Rows joined:** {len(merged)}",
                f"**Correlation:** {correlation:.3f}" if pd.notna(correlation) else "**Correlation:** n/a",
                f"**Primary mean:** {primary.mean():.4f}" if primary.notna().any() else "**Primary mean:** n/a",
                f"**Compare mean:** {secondary.mean():.4f}" if secondary.notna().any() else "**Compare mean:** n/a",
                (
                    f"**{focus_col.title()} mean:** {pd.to_numeric(merged[focus_col], errors='coerce').mean():.4f}"
                    if pd.to_numeric(merged[focus_col], errors="coerce").notna().any()
                    else f"**{focus_col.title()} mean:** n/a"
                ),
            ]
        )
        sample_cols = [*join_keys, self._table.value, other_table, "difference", "ratio"]
        return summary, merged[sample_cols].head(self._limit.value)

    def _resolve_spatial_columns(self, df: pd.DataFrame) -> tuple[str | None, str | None]:
        lat_col = _resolve_role_column(self.state, df, "latitude")
        lon_col = _resolve_role_column(self.state, df, "longitude")
        return lat_col, lon_col

    def _style_plot(self, plot) -> None:
        plot.toolbar.logo = None
        plot.toolbar_location = "above"
        plot.background_fill_color = "#ffffff"
        plot.border_fill_color = "#ffffff"
        plot.outline_line_color = "#d9e1ea"
        plot.grid.grid_line_color = "#e5e7eb"
        plot.grid.grid_line_alpha = 1.0
        plot.axis.axis_line_color = "#9aa4b2"
        plot.axis.major_tick_line_color = "#9aa4b2"
        plot.axis.minor_tick_line_color = None
        plot.axis.major_label_text_color = "#4b5563"
        plot.axis.axis_label_text_color = "#4b5563"
        plot.title.text_color = "#1f2937"

    def _build_plot(self, df: pd.DataFrame):
        x = self._x.value
        y = self._y.value
        chart_type = self._chart_type.value
        if df.empty:
            return pn.pane.Markdown("No chartable data for the current selection.")

        if chart_type == "spatial":
            lat_col, lon_col = self._resolve_spatial_columns(df)
            if lat_col is None or lon_col is None:
                return pn.pane.Markdown("Spatial view requires latitude and longitude coordinates in the current table.")

            spatial = self._aggregate_spatial_dataframe(df, lat_col, lon_col, y)
            if spatial.empty:
                return pn.pane.Markdown("Spatial view requires numeric latitude, longitude, and value columns.")

            low = float(spatial["__value__"].min())
            high = float(spatial["__value__"].max())
            if low == high:
                high = low + 1.0
            mapper = LinearColorMapper(palette=Blues256, low=low, high=high)
            source = ColumnDataSource(spatial)
            plot = figure(
                height=380,
                sizing_mode="stretch_width",
                title=f"Spatial view: {y}",
                x_axis_label=lon_col,
                y_axis_label=lat_col,
            )
            plot.scatter(
                "__lon__",
                "__lat__",
                source=source,
                marker="square",
                size=12,
                fill_alpha=0.95,
                line_color=None,
                fill_color={"field": "__value__", "transform": mapper},
            )
            plot.add_tools(
                HoverTool(
                    tooltips=[
                        (lon_col, "@__lon__"),
                        (lat_col, "@__lat__"),
                        (y, "@__value__"),
                    ]
                )
            )
            plot.add_layout(
                ColorBar(
                    color_mapper=mapper,
                    ticker=BasicTicker(desired_num_ticks=6),
                    title=y,
                ),
                "right",
            )
            self._style_plot(plot)
            return plot

        if x not in df.columns or y not in df.columns:
            return pn.pane.Markdown("No chartable data for the current selection.")

        if chart_type == "histogram":
            series = pd.to_numeric(df[y], errors="coerce").dropna()
            if series.empty:
                return pn.pane.Markdown("Histogram requires a numeric y column.")
            hist, edges = np.histogram(series, bins=min(max(self._plot_resolution.value // 10, 8), 40))
            plot = figure(height=380, sizing_mode="stretch_width", title=f"{y} distribution")
            plot.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], fill_color="#1976d2", line_color="#1565c0")
            self._style_plot(plot)
            return plot

        chart_df = self._downsample_frame(df, order_by=x if chart_type in {"line", "scatter"} else None)
        axis_type = "datetime" if pd.api.types.is_datetime64_any_dtype(df[x]) else "auto"
        plot = figure(height=380, sizing_mode="stretch_width", title=f"{chart_type.title()} plot: {y} vs {x}", x_axis_type=axis_type)
        source = ColumnDataSource(chart_df.assign(__x__=chart_df[x], __y__=chart_df[y]))

        if chart_type == "line":
            ordered = chart_df.sort_values(x)
            source = ColumnDataSource(ordered.assign(__x__=ordered[x], __y__=ordered[y]))
            plot.line("__x__", "__y__", line_width=3, color="#1976d2", source=source)
            plot.scatter("__x__", "__y__", size=7, color="#64b5f6", line_color="#1565c0", source=source)
        elif chart_type == "scatter":
            plot.scatter("__x__", "__y__", size=8, fill_color="#42a5f5", line_color="#1565c0", fill_alpha=0.85, source=source)
        elif chart_type == "bar":
            grouped = chart_df.groupby(x, dropna=False)[y].mean().reset_index()
            grouped[x] = grouped[x].astype(str)
            source = ColumnDataSource(grouped.assign(__x__=grouped[x], __y__=grouped[y]))
            plot = figure(
                height=380,
                sizing_mode="stretch_width",
                title=f"Mean {y} by {x}",
                x_range=list(grouped[x]),
            )
            plot.vbar(x="__x__", top="__y__", width=0.8, color="#1976d2", source=source)

        plot.add_tools(HoverTool(tooltips=[(x, "@__x__"), (y, "@__y__")]))
        self._style_plot(plot)
        return plot

    def _export_csv(self) -> StringIO:
        buffer = StringIO()
        self.current_dataframe().to_csv(buffer, index=False)
        buffer.seek(0)
        return buffer

    def _export_json(self) -> StringIO:
        buffer = StringIO(self.current_dataframe().to_json(orient="records", date_format="iso", indent=2))
        buffer.seek(0)
        return buffer

    def _build_field_inventory_html(self) -> str:
        columns = self._table_columns(self._table.value)
        numeric = self._numeric_columns(self._table.value)
        role_chunks = []
        for role in ROLE_ORDER:
            name = self.state.coord_map.get(role)
            if name is None or name not in columns:
                continue
            meta = self.state.coord_metadata.get(name, {})
            confidence = meta.get("confidence", "none")
            role_chunks.append(
                "<div class='lxl-field-chip'>"
                f"<span>{role}</span>"
                f"<strong>{name}</strong>"
                f"<em>{confidence}</em>"
                "</div>"
            )
        if not role_chunks:
            role_chunks.append("<div class='lxl-field-chip'><span>roles</span><strong>none</strong><em>n/a</em></div>")

        queryable_dims = ", ".join(_dimension_info_for_table(self.state, self._table.value)) or "none"
        numeric_label = ", ".join(numeric[:5]) if numeric else "none"
        if len(numeric) > 5:
            numeric_label += f" +{len(numeric) - 5} more"
        return (
            "<div class='lxl-field-grid'>"
            "<div>"
            "<div class='lxl-explorer-label'>Detected roles</div>"
            f"<div class='lxl-field-chip-row'>{''.join(role_chunks)}</div>"
            "</div>"
            "<div>"
            "<div class='lxl-explorer-label'>Queryable dimensions</div>"
            f"<div class='lxl-field-copy'>{queryable_dims}</div>"
            "</div>"
            "<div>"
            "<div class='lxl-explorer-label'>Numeric fields</div>"
            f"<div class='lxl-field-copy'>{numeric_label}</div>"
            "</div>"
            "</div>"
        )

    def _build_selection_banner_html(self, df: pd.DataFrame) -> str:
        lat_col, lon_col = self._resolve_spatial_columns(df)
        compare_label = self._compare_table.value if self._compare_table.value != "None" else "off"
        spatial_label = "ready" if lat_col and lon_col else "unavailable"
        return (
            "<div class='lxl-selection-banner'>"
            f"<div><span class='lxl-explorer-label'>Table</span><strong>{self._table.value}</strong></div>"
            f"<div><span class='lxl-explorer-label'>Rows</span><strong>{len(df)}</strong></div>"
            f"<div><span class='lxl-explorer-label'>X / Y</span><strong>{self._x.value} / {self._y.value}</strong></div>"
            f"<div><span class='lxl-explorer-label'>Chart</span><strong>{self._chart_type.value}</strong></div>"
            f"<div><span class='lxl-explorer-label'>Spatial</span><strong>{spatial_label}</strong></div>"
            f"<div><span class='lxl-explorer-label'>Compare</span><strong>{compare_label}</strong></div>"
            "</div>"
        )

    def _on_table_search(self, event=None) -> None:
        if event is None or not event.new or event.new == self._table.value:
            return
        if event.new in self.state.tables:
            self._table.value = event.new

    def _on_table_change(self, event=None) -> None:
        self._table_search.value = self._table.value
        self._rebuild_filters()
        self._sync_axis_options()
        self._sync_compare_options()
        self._update_outputs()

    def _update_outputs(self, event=None) -> None:
        self._compare_mode.disabled = self._compare_table.value == "None"
        self._time_window.disabled = self._time_mode.value != "rolling mean"

        df = self.current_dataframe()
        query_cost = self.current_query_cost()
        stats_df = self._build_statistics_dataframe(df)
        coverage_df = self._build_coverage_dataframe(df)
        compare_summary, compare_df = self._build_comparison_dataframe(df)
        time_summary, time_plot = self._build_time_analysis_output()

        filter_count = len(self._collect_query())
        compare_label = self._compare_table.value if self._compare_table.value != "None" else "off"

        self._selection_banner.object = self._build_selection_banner_html(df)
        self._field_inventory.object = self._build_field_inventory_html()
        self._dataset_info.object = self._build_dataset_info_html()
        self._cf_table.value = self._build_cf_dataframe()
        self._attribute_preview.object = self._build_attribute_preview()
        self._query_cost.object = self._build_query_cost_html(query_cost, len(df))
        self._query_warning.object = (
            f"**Estimate note:** {query_cost['warning']}"
            if query_cost.get("warning")
            else "**Estimate note:** current selection looks safe to preview and chart."
        )
        self._summary.object = (
            "<div class='lxl-explorer-summary'>"
            f"<div><span class='lxl-explorer-label'>Table rows</span><strong>{self._table_row_count(self._table.value)}</strong></div>"
            f"<div><span class='lxl-explorer-label'>Selection rows</span><strong>{len(df)}</strong></div>"
            f"<div><span class='lxl-explorer-label'>Filters</span><strong>{filter_count}</strong></div>"
            f"<div><span class='lxl-explorer-label'>Value field</span><strong>{self._table.value}</strong></div>"
            f"<div><span class='lxl-explorer-label'>Compare</span><strong>{compare_label}</strong></div>"
            f"<div><span class='lxl-explorer-label'>Risk</span><strong>{query_cost['risk']}</strong></div>"
            "</div>"
        )
        self._active_filters.object = "\n".join(self._active_filter_lines())
        self._status.object = (
            f"**Rows returned:** {len(df)}  \n"
            f"**Chart:** `{self._chart_type.value}`  \n"
            f"**X / Y:** `{self._x.value}` / `{self._y.value}`  \n"
            f"**Compare:** `{compare_label}`  \n"
            f"**Estimated full rows:** `{query_cost['selected_rows']:,}`"
        )
        self._data.value = df
        self._stats.value = stats_df
        self._time_summary.object = time_summary
        self._coverage_summary.object = (
            f"**Selection coverage:** {len(df)} of {self._table_row_count(self._table.value)} rows "
            f"for `{self._table.value}`."
        )
        self._coverage_table.value = coverage_df
        self._compare_summary.object = compare_summary
        self._compare_table_view.value = compare_df
        self._query.object = f"```python\n{self.source_query_text()}\n```"
        self._sql.object = f"```sql\n{self.sql_preview_text()}\n```"
        self._chart.objects = [pn.panel(self._build_plot(df), sizing_mode="stretch_width")]
        self._time_plot.objects = [pn.panel(time_plot, sizing_mode="stretch_width")]

        slug = self._table.value.replace(" ", "_")
        self._download_csv.filename = f"{slug}_selection.csv"
        self._download_json.filename = f"{slug}_selection.json"

    def __panel__(self):
        return self._layout
