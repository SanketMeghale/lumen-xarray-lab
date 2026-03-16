from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import panel as pn
import param

from bokeh.models import ColumnDataSource, HoverTool
from bokeh.plotting import figure
from panel.viewable import Viewer

from .state import DashboardState


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


class ExplorerView(Viewer):
    state = param.Parameter()

    def __init__(self, **params: Any):
        super().__init__(**params)
        self._filter_widgets: dict[str, pn.widgets.Widget] = {}

        self._table = pn.widgets.Select(name="Table", options=self.state.tables, value=self.state.table)
        self._chart_type = pn.widgets.Select(
            name="Chart",
            options=["line", "scatter", "bar", "histogram"],
            value="line",
        )
        self._x = pn.widgets.Select(name="X axis", options=[])
        self._y = pn.widgets.Select(name="Y axis", options=[])
        self._limit = pn.widgets.IntSlider(name="Row limit", start=25, end=1000, step=25, value=250)

        self._filters = pn.Column(sizing_mode="stretch_width")
        self._query = pn.pane.Markdown(sizing_mode="stretch_width", css_classes=["lxl-card-markdown"])
        self._sql = pn.pane.Markdown(sizing_mode="stretch_width", css_classes=["lxl-card-markdown"])
        self._chart = pn.Column(sizing_mode="stretch_width", min_height=420)
        self._data = pn.widgets.Tabulator(pd.DataFrame(), pagination="local", page_size=12, sizing_mode="stretch_width")
        self._status = pn.pane.Markdown(css_classes=["lxl-card-markdown"])
        self._summary = pn.pane.HTML(sizing_mode="stretch_width")
        self._active_filters = pn.pane.Markdown(css_classes=["lxl-card-markdown"])

        self._table.param.watch(self._on_table_change, "value")
        for widget in (self._chart_type, self._x, self._y, self._limit):
            widget.param.watch(self._update_outputs, "value")

        self._rebuild_filters()
        self._sync_axis_options()
        self._update_outputs()

        controls = pn.Column(
            pn.pane.HTML("<div class='lxl-explorer-section-title'>Explorer Controls</div>"),
            self._table,
            self._chart_type,
            self._x,
            self._y,
            self._limit,
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

    def _active_filter_lines(self) -> list[str]:
        filters = self._collect_query()
        if not filters:
            return ["**Active filters:** none"]
        lines = ["**Active filters**"]
        for key, value in filters.items():
            if isinstance(value, tuple) and len(value) == 2:
                lines.append(f"- `{key}` between `{value[0]}` and `{value[1]}`")
            else:
                lines.append(f"- `{key}` = `{value}`")
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

    def _build_plot(self, df: pd.DataFrame):
        x = self._x.value
        y = self._y.value
        chart_type = self._chart_type.value
        if df.empty or x not in df.columns or y not in df.columns:
            return pn.pane.Markdown("No chartable data for the current selection.")

        if chart_type == "histogram":
            series = pd.to_numeric(df[y], errors="coerce").dropna()
            if series.empty:
                return pn.pane.Markdown("Histogram requires a numeric y column.")
            hist, edges = np.histogram(series, bins=min(20, max(5, len(series))))
            plot = figure(height=360, sizing_mode="stretch_width", title=f"{y} distribution")
            plot.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], fill_color="#117864", line_color="#0b3d38")
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

    def _on_table_change(self, event=None) -> None:
        self._rebuild_filters()
        self._sync_axis_options()
        self._update_outputs()

    def _update_outputs(self, event=None) -> None:
        df = self.current_dataframe()
        filter_count = len(self._collect_query())
        self._summary.object = (
            "<div class='lxl-explorer-summary'>"
            f"<div><span class='lxl-explorer-label'>Table</span><strong>{self._table.value}</strong></div>"
            f"<div><span class='lxl-explorer-label'>Rows</span><strong>{len(df)}</strong></div>"
            f"<div><span class='lxl-explorer-label'>Filters</span><strong>{filter_count}</strong></div>"
            f"<div><span class='lxl-explorer-label'>Chart</span><strong>{self._chart_type.value}</strong></div>"
            "</div>"
        )
        self._active_filters.object = "\n".join(self._active_filter_lines())
        self._status.object = (
            f"**Rows returned:** {len(df)}  \n"
            f"**Chart:** `{self._chart_type.value}`  \n"
            f"**X / Y:** `{self._x.value}` / `{self._y.value}`"
        )
        self._data.value = df
        self._query.object = f"```python\n{self.source_query_text()}\n```"
        self._sql.object = f"```sql\n{self.sql_preview_text()}\n```"
        self._chart.objects = [pn.panel(self._build_plot(df), sizing_mode="stretch_width")]

    def __panel__(self):
        return self._layout
