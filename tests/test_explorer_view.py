from __future__ import annotations

import json

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


def test_explorer_spatial_chart_renders(synthetic_dataset):
    state = DashboardState.from_dataset(synthetic_dataset)
    explorer = ExplorerView(state=state)
    explorer._chart_type.value = "spatial"
    plot = explorer._build_plot(explorer.current_dataframe())
    assert isinstance(plot, LayoutDOM)


def test_explorer_statistics_and_coverage(synthetic_dataset):
    state = DashboardState.from_dataset(synthetic_dataset)
    explorer = ExplorerView(state=state)
    df = explorer.current_dataframe()
    stats = explorer._build_statistics_dataframe(df)
    coverage = explorer._build_coverage_dataframe(df)

    assert "mean" in stats.columns
    assert "temperature" in stats["column"].tolist()
    assert set(coverage["dimension"]) == {"time", "lat", "lon"}
    assert coverage["selected_unique"].min() >= 1


def test_explorer_builds_time_analysis_and_query_cost(synthetic_dataset):
    state = DashboardState.from_dataset(synthetic_dataset)
    explorer = ExplorerView(state=state)
    explorer._time_mode.value = "trend"

    summary, plot = explorer._build_time_analysis_output()
    cost = explorer.current_query_cost()

    assert "Time dimension" in summary
    assert "Trend slope" in summary
    assert isinstance(plot, LayoutDOM)
    assert cost["selected_rows"] == 8
    assert cost["risk"] in {"low", "medium", "high"}


def test_explorer_builds_dataset_info_and_cf_metadata(synthetic_dataset):
    state = DashboardState.from_dataset(synthetic_dataset)
    explorer = ExplorerView(state=state)

    dataset_info = explorer._build_dataset_info_html()
    cf_frame = explorer._build_cf_dataframe()

    assert "Untitled dataset" in dataset_info
    assert "temperature" in dataset_info
    assert set(cf_frame["coordinate"]) == {"time", "lat", "lon"}


def test_explorer_builds_comparison_dataframe(multi_table_dataset):
    state = DashboardState.from_dataset(multi_table_dataset)
    explorer = ExplorerView(state=state)
    explorer._compare_table.value = "humidity"
    summary, compare_df = explorer._build_comparison_dataframe(explorer.current_dataframe())

    assert "Correlation" in summary
    assert "difference" in compare_df.columns
    assert "ratio" in compare_df.columns
    assert len(compare_df) >= 1


def test_explorer_exports_current_selection(synthetic_dataset):
    state = DashboardState.from_dataset(synthetic_dataset)
    explorer = ExplorerView(state=state)

    csv_text = explorer._export_csv().getvalue()
    json_text = explorer._export_json().getvalue()

    assert "temperature" in csv_text
    records = json.loads(json_text)
    assert records
    assert "temperature" in records[0]


def test_explorer_uses_dataset_sampling_instead_of_source_get(synthetic_dataset):
    state = DashboardState.from_dataset(synthetic_dataset)

    def fail_get(*args, **kwargs):
        raise AssertionError("Explorer should not call source.get() for sampled views.")

    state.source.get = fail_get
    explorer = ExplorerView(state=state)

    df = explorer.current_dataframe()

    assert not df.empty
    assert "temperature" in df.columns
