from __future__ import annotations

from bokeh.models.layouts import LayoutDOM

from lumen_xarray_lab.dashboard.explorer import ExplorerView
from lumen_xarray_lab.dashboard.state import DashboardState


def test_explorer_view_builds_dataframe_and_queries(synthetic_dataset):
    state = DashboardState.from_dataset(synthetic_dataset)
    explorer = ExplorerView(state=state)
    df = explorer.current_dataframe()
    assert "temperature" in df.columns
    assert "source.get(" in explorer.source_query_text()
    assert 'SELECT * FROM "temperature"' in explorer.sql_preview_text()


def test_explorer_view_renders_plot(synthetic_dataset):
    state = DashboardState.from_dataset(synthetic_dataset)
    explorer = ExplorerView(state=state)
    plot = explorer._build_plot(explorer.current_dataframe())
    assert isinstance(plot, LayoutDOM)


def test_explorer_filters_affect_query(synthetic_dataset):
    state = DashboardState.from_dataset(synthetic_dataset)
    explorer = ExplorerView(state=state)
    time_widget = explorer.filter_widgets["time"]
    time_widget.value = (time_widget.start, time_widget.start)
    explorer.filter_widgets["lat"].value = (10.0, 10.0)
    query = explorer.source_query_text()
    assert "time" in query
    assert "lat" in query
    assert len(explorer.current_dataframe()) == 2


def test_explorer_switches_tables_and_chart_modes(multi_table_dataset):
    state = DashboardState.from_dataset(multi_table_dataset)
    explorer = ExplorerView(state=state)
    explorer._table.value = "humidity"

    df = explorer.current_dataframe()
    assert "humidity" in df.columns
    assert explorer._y.value == "humidity"
    assert '"humidity"' in explorer.sql_preview_text()

    for chart_type in ("line", "scatter", "bar", "histogram"):
        explorer._chart_type.value = chart_type
        plot = explorer._build_plot(df)
        assert isinstance(plot, LayoutDOM)


def test_explorer_query_panels_include_filter_summary(synthetic_dataset):
    state = DashboardState.from_dataset(synthetic_dataset)
    explorer = ExplorerView(state=state)
    time_widget = explorer.filter_widgets["time"]
    time_widget.value = (time_widget.start, time_widget.start)
    explorer._update_outputs()
    assert "Active filters" in explorer._active_filters.object
    assert "BETWEEN" in explorer.sql_preview_text()
