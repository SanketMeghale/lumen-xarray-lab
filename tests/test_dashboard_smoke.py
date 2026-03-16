from __future__ import annotations

import panel as pn

from lumen_xarray_lab.dashboard.app import create_dashboard
from lumen_xarray_lab.dashboard.state import DashboardState


def _find_tabs(view):
    found = []
    if isinstance(view, pn.Tabs):
        found.append(view)
    children = getattr(view, "objects", None)
    if not children:
        return found
    for child in children:
        found.extend(_find_tabs(child))
    return found


def test_create_dashboard(synthetic_dataset):
    dashboard = create_dashboard(synthetic_dataset)
    assert dashboard.title == "lumen-xarray-lab"
    assert len(dashboard.main) == 1
    tabs = _find_tabs(dashboard.main[0])
    assert any(len(tab) == 5 for tab in tabs)


def test_dashboard_state_has_runtime_and_dimensions(synthetic_dataset):
    state = DashboardState.from_dataset(synthetic_dataset)
    assert state.runtime_source in {"lumen-xarray-source", "lab-adapter"}
    assert state.tables == ["temperature"]
    assert "time" in state.dimension_info
    assert "mode" in state.runtime_details


def test_dashboard_controller_loads_from_uri(tmp_path, synthetic_dataset):
    path = tmp_path / "synthetic.nc"
    dataset = synthetic_dataset.copy(deep=True)
    for variable in dataset.variables:
        dataset[variable].encoding = {}
    dataset.to_netcdf(path)

    dashboard = create_dashboard()
    controller = dashboard._dashboard_controller
    controller.load_from_uri(str(path))

    assert controller.state.tables == ["temperature"]
    assert "synthetic.nc" in controller._loader_status.object


def test_dashboard_controller_loads_uploaded_file(synthetic_dataset):
    payload = synthetic_dataset.to_netcdf()
    dashboard = create_dashboard()
    controller = dashboard._dashboard_controller

    controller.load_from_upload("uploaded.nc", payload)

    assert controller.state.tables == ["temperature"]
    assert "uploaded.nc" in controller._loader_summary.object


def test_dashboard_controller_normalizes_repo_relative_paths(tmp_path, synthetic_dataset, monkeypatch):
    path = tmp_path / "relative.nc"
    dataset = synthetic_dataset.copy(deep=True)
    for variable in dataset.variables:
        dataset[variable].encoding = {}
    dataset.to_netcdf(path)

    dashboard = create_dashboard()
    controller = dashboard._dashboard_controller
    monkeypatch.setattr(controller, "_repo_root", tmp_path)

    controller._path_input.value = "relative.nc"
    controller._on_load_path()

    assert controller.state.tables == ["temperature"]
    assert str(path) in controller._loader_status.object


def test_dashboard_controller_removes_stale_uploaded_files(synthetic_dataset):
    payload = synthetic_dataset.to_netcdf()
    dashboard = create_dashboard()
    controller = dashboard._dashboard_controller

    controller.load_from_upload("uploaded.nc", payload)
    upload_path = controller._active_upload_path

    assert upload_path is not None
    assert upload_path.exists()

    controller.load_demo()

    assert not upload_path.exists()
