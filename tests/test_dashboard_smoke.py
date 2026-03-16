from __future__ import annotations

from lumen_xarray_lab.dashboard.app import create_dashboard
from lumen_xarray_lab.dashboard.state import DashboardState


def test_create_dashboard(synthetic_dataset):
    dashboard = create_dashboard(synthetic_dataset)
    assert dashboard.title == "lumen-xarray-lab"
    assert len(dashboard.main) == 1
    tabs = dashboard.main[0][2]
    assert len(tabs) == 5


def test_dashboard_state_has_runtime_and_dimensions(synthetic_dataset):
    state = DashboardState.from_dataset(synthetic_dataset)
    assert state.runtime_source in {"lumen-xarray-source", "lab-adapter"}
    assert state.tables == ["temperature"]
    assert "time" in state.dimension_info
    assert "mode" in state.runtime_details
