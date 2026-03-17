from __future__ import annotations

from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def _load_module(filename: str):
    path = EXAMPLES / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_quickstart_summary():
    module = _load_module("quickstart.py")
    summary = module.collect_summary()
    assert "tables" in summary
    assert len(summary["tables"]) >= 1


def test_air_temperature_demo():
    module = _load_module("air_temperature_demo.py")
    report = module.build_report()
    assert "preview_columns" in report
    assert report["preview_rows"] >= 1


def test_ai_upload_demo():
    module = _load_module("ai_upload_demo.py")
    preview = module.run_demo()
    assert "tables" in preview
    assert "cli_example" in preview


def test_sql_explorer_demo():
    module = _load_module("sql_explorer_demo.py")
    status = module.get_status()
    assert status["available"] is True
    assert status["result_rows"] >= 1


def test_dashboard_app():
    module = _load_module("dashboard_app.py")
    app = module.build_app()
    assert app.title == "lumen-xarray-lab"


def test_quickstart_runtime_details():
    module = _load_module("quickstart.py")
    summary = module.collect_summary()
    assert "runtime_details" in summary
    assert "mode" in summary["runtime_details"]
