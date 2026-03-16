from __future__ import annotations

from io import StringIO
from typing import Any

import numpy as np
import pandas as pd
import panel as pn
import param

from bokeh.models import BasicTicker, ColorBar, ColumnDataSource, HoverTool, LinearColorMapper
from bokeh.palettes import Viridis256
from bokeh.plotting import figure
from panel.viewable import Viewer

from .state import DashboardState

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

        self._table = pn.widgets.Select(name="Table", options=self.state.tables, value=self.state.table)
        self._chart_type = pn.widgets.Select(
            name="Chart",
            options=["line", "scatter", "bar", "histogram", "spatial"],
            value="line",
        )
        self._x = pn.widgets.Select(name="X axis", options=[])
        self._y = pn.widgets.Select(name="Y axis", options=[])
        self._limit = pn.widgets.IntSlider(name="Row limit", start=25, end=1000, step=25, value=250)
        self._compare_table = pn.widgets.Select(name="Compare table", options=["None"], value="None")
        self._compare_mode = pn.widgets.Select(name="Compare mode", options=["difference", "ratio"], value="difference")

        self._filters = pn.Column(sizing_mode="stretch_width")
        self._query = pn.pane.Markdown(sizing_mode="stretch_width", css_classes=["lxl-card-markdown"])
        self._sql = pn.pane.Markdown(sizing_mode="stretch_width", css_classes=["lxl-card-markdown"])
        self._chart = pn.Column(sizing_mode="stretch_width", min_height=420)
        self._data = pn.widgets.Tabulator(pd.DataFrame(), pagination="local", page_size=12, sizing_mode="stretch_width")
        self._stats = pn.widgets.Tabulator(pd.DataFrame(), pagination="local", page_size=10, sizing_mode="stretch_width")
        self._coverage_table = pn.widgets.Tabulator(pd.DataFrame(), pagination="local", page_size=10, sizing_mode="stretch_width")
        self._compare_table_view = pn.widgets.Tabulator(pd.DataFrame(), pagination="local", page_size=10, sizing_mode="stretch_width")
        self._coverage_summary = pn.pane.Markdown(css_classes=["lxl-card-markdown"])
        self._compare_summary = pn.pane.Markdown(css_classes=["lxl-card-markdown"])
        self._status = pn.pane.Markdown(css_classes=["lxl-card-markdown"])
        self._summary = pn.pane.HTML(sizing_mode="stretch_width")
        self._active_filters = pn.pane.Markdown(css_classes=["lxl-card-markdown"])
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

        self._table.param.watch(self._on_table_change, "value")
        for widget in (
            self._chart_type,
            self._x,
            self._y,
            self._limit,
            self._compare_table,
            self._compare_mode,
        ):
            widget.param.watch(self._update_outputs, "value")

        self._rebuild_filters()
        self._sync_axis_options()
        self._sync_compare_options()
        self._update_outputs()

        controls = pn.Column(
            pn.pane.HTML("<div class='lxl-explorer-section-title'>Explorer Controls</div>"),
            self._table,
            self._chart_type,
            self._x,
            self._y,
            self._limit,
            pn.pane.HTML("<div class='lxl-explorer-section-title'>Compare / Export</div>"),
            self._compare_table,
            self._compare_mode,
            pn.Row(self._download_csv, self._download_json, sizing_mode="stretch_width"),
            pn.pane.HTML("<div class='lxl-explorer-section-title'>Dimension Filters</div>"),
            self._filters,
            self._status,
            sizing_mode="stretch_width",
        )
        self._layout = pn.Row(
            pn.Card(
                controls,
                title="Dataset Explorer",
                collapsed=False,
                sizing_mode="stretch_width",
                styles={"border-radius": "18px"},
                min_width=360,
            ),
            pn.Column(
                pn.Card(
                    pn.Column(
                        self._summary,
                        self._active_filters,
                        pn.Tabs(
                            ("Chart", self._chart),
                            ("Data", self._data),
                            ("Statistics", self._stats),
                            (
                                "Compare",
                                pn.Column(self._compare_summary, self._compare_table_view, sizing_mode="stretch_width"),
                            ),
                            (
                                "Coverage",
                                pn.Column(self._coverage_summary, self._coverage_table, sizing_mode="stretch_width"),
                            ),
                            ("Source Query", self._query),
                            ("Pseudo SQL", self._sql),
                        ),
                        sizing_mode="stretch_width",
                    ),
                    title="Explorer Output",
                    collapsed=False,
                    sizing_mode="stretch_width",
                    styles={"border-radius": "18px"},
                ),
                sizing_mode="stretch_width",
            ),
            sizing_mode="stretch_width",
        )

    @property
    def filter_widgets(self) -> dict[str, pn.widgets.Widget]:
        return self._filter_widgets

    def _table_columns(self, table: str) -> list[str]:
        return list(self.state.dataset[table].to_dataframe(name=table).reset_index().columns)

    def _numeric_columns(self, table: str) -> list[str]:
        df = self.state.dataset[table].to_dataframe(name=table).reset_index()
        return [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]

    def _default_filter_value(self, spec: dict[str, Any]) -> Any:
        if spec["type"] == "datetime":
            values = pd.to_datetime(spec["values"])
            return (values.min().to_pydatetime(), values.max().to_pydatetime())
        if spec["type"] == "numeric":
            values = np.asarray(spec["values"], dtype=float)
            return (float(np.min(values)), float(np.max(values)))
        return "All"

    def _rebuild_filters(self) -> None:
        self._filter_widgets.clear()
        self._filters.objects = []
        dim_info = _dimension_info_for_table(self.state, self._table.value)
        widgets: list[pn.viewable.Viewable] = []

        for name, spec in dim_info.items():
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

    def _sync_axis_options(self) -> None:
        columns = self._table_columns(self._table.value)
        numeric = self._numeric_columns(self._table.value)
        default_y = self._table.value if self._table.value in numeric else (numeric[0] if numeric else columns[-1])
        default_x = next((col for col in columns if col != default_y), columns[0])
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

    def current_dataframe(self) -> pd.DataFrame:
        df = self.state.source.get(self._table.value, **self._collect_query())
        return df.head(self._limit.value)

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
            other_df = self.state.source.get(other_table, **self._collect_query()).head(self._limit.value)
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

            spatial = df.copy()
            spatial["__lon__"] = pd.to_numeric(spatial[lon_col], errors="coerce")
            spatial["__lat__"] = pd.to_numeric(spatial[lat_col], errors="coerce")
            spatial["__value__"] = pd.to_numeric(spatial[y], errors="coerce")
            spatial = spatial.dropna(subset=["__lon__", "__lat__", "__value__"])
            if spatial.empty:
                return pn.pane.Markdown("Spatial view requires numeric latitude, longitude, and value columns.")

            low = float(spatial["__value__"].min())
            high = float(spatial["__value__"].max())
            if low == high:
                high = low + 1.0
            mapper = LinearColorMapper(palette=Viridis256, low=low, high=high)
            source = ColumnDataSource(spatial)
            plot = figure(
                height=360,
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
            plot.toolbar.logo = None
            plot.toolbar_location = "above"
            return plot

        if x not in df.columns or y not in df.columns:
            return pn.pane.Markdown("No chartable data for the current selection.")

        if chart_type == "histogram":
            series = pd.to_numeric(df[y], errors="coerce").dropna()
            if series.empty:
                return pn.pane.Markdown("Histogram requires a numeric y column.")
            hist, edges = np.histogram(series, bins=min(20, max(5, len(series))))
            plot = figure(height=360, sizing_mode="stretch_width", title=f"{y} distribution")
            plot.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], fill_color="#117864", line_color="#0b3d38")
            plot.toolbar.logo = None
            plot.toolbar_location = "above"
            return plot

        axis_type = "datetime" if pd.api.types.is_datetime64_any_dtype(df[x]) else "auto"
        plot = figure(height=360, sizing_mode="stretch_width", title=f"{chart_type.title()} plot: {y} vs {x}", x_axis_type=axis_type)
        source = ColumnDataSource(df.assign(__x__=df[x], __y__=df[y]))

        if chart_type == "line":
            ordered = df.sort_values(x)
            source = ColumnDataSource(ordered.assign(__x__=ordered[x], __y__=ordered[y]))
            plot.line("__x__", "__y__", line_width=2, color="#117864", source=source)
            plot.scatter("__x__", "__y__", size=7, color="#cf7f29", source=source)
        elif chart_type == "scatter":
            plot.scatter("__x__", "__y__", size=8, fill_color="#117864", line_color="#0b3d38", fill_alpha=0.85, source=source)
        elif chart_type == "bar":
            grouped = df.groupby(x, dropna=False)[y].mean().reset_index()
            grouped[x] = grouped[x].astype(str)
            source = ColumnDataSource(grouped.assign(__x__=grouped[x], __y__=grouped[y]))
            plot = figure(
                height=360,
                sizing_mode="stretch_width",
                title=f"Mean {y} by {x}",
                x_range=list(grouped[x]),
            )
            plot.vbar(x="__x__", top="__y__", width=0.8, color="#117864", source=source)

        plot.add_tools(HoverTool(tooltips=[(x, "@__x__"), (y, "@__y__")]))
        plot.toolbar.logo = None
        plot.toolbar_location = "above"
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

    def _on_table_change(self, event=None) -> None:
        self._rebuild_filters()
        self._sync_axis_options()
        self._sync_compare_options()
        self._update_outputs()

    def _update_outputs(self, event=None) -> None:
        self._compare_mode.disabled = self._compare_table.value == "None"

        df = self.current_dataframe()
        stats_df = self._build_statistics_dataframe(df)
        coverage_df = self._build_coverage_dataframe(df)
        compare_summary, compare_df = self._build_comparison_dataframe(df)

        filter_count = len(self._collect_query())
        compare_label = self._compare_table.value if self._compare_table.value != "None" else "off"
        self._summary.object = (
            "<div class='lxl-explorer-summary'>"
            f"<div><span class='lxl-explorer-label'>Table</span><strong>{self._table.value}</strong></div>"
            f"<div><span class='lxl-explorer-label'>Rows</span><strong>{len(df)}</strong></div>"
            f"<div><span class='lxl-explorer-label'>Filters</span><strong>{filter_count}</strong></div>"
            f"<div><span class='lxl-explorer-label'>Chart</span><strong>{self._chart_type.value}</strong></div>"
            f"<div><span class='lxl-explorer-label'>Compare</span><strong>{compare_label}</strong></div>"
            "</div>"
        )
        self._active_filters.object = "\n".join(self._active_filter_lines())
        self._status.object = (
            f"**Rows returned:** {len(df)}  \n"
            f"**Chart:** `{self._chart_type.value}`  \n"
            f"**X / Y:** `{self._x.value}` / `{self._y.value}`  \n"
            f"**Compare:** `{compare_label}`"
        )
        self._data.value = df
        self._stats.value = stats_df
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

        slug = self._table.value.replace(" ", "_")
        self._download_csv.filename = f"{slug}_selection.csv"
        self._download_json.filename = f"{slug}_selection.json"

    def __panel__(self):
        return self._layout
