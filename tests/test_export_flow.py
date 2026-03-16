from __future__ import annotations

from pathlib import Path

from lumen_xarray_lab.dashboard.export_flow import (
    build_capture_plan,
    export_dashboard_html,
    write_capture_manifest,
)


def test_build_capture_plan():
    plan = build_capture_plan("C:/tmp/lumen-xarray-lab")
    assert str(plan.html_path).endswith("docs\\screenshots\\dashboard_snapshot.html")
    assert str(plan.gif_path).endswith("docs\\gifs\\dashboard_walkthrough.gif")


def test_export_dashboard_html(tmp_path, synthetic_dataset):
    output = export_dashboard_html(tmp_path / "snapshot.html", dataset=synthetic_dataset)
    assert output.exists()
    assert "<html" in output.read_text(encoding="utf-8", errors="ignore").lower()


def test_write_capture_manifest(tmp_path):
    plan = build_capture_plan(tmp_path)
    manifest = write_capture_manifest(plan, screenshot_mode="html-only", notes=["ok"])
    assert manifest.exists()
    text = manifest.read_text(encoding="utf-8")
    assert "html-only" in text
