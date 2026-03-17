from __future__ import annotations

from pathlib import Path

import imageio.v2 as imageio
import numpy as np

from lumen_xarray_lab.dashboard.export_flow import (
    build_capture_plan,
    export_dashboard_html,
    feature_gallery_captures,
    real_world_gallery_captures,
    make_gif_from_frames,
    write_capture_manifest,
)


def test_build_capture_plan():
    plan = build_capture_plan("C:/tmp/lumen-xarray-lab")
    assert str(plan.html_path).endswith("docs\\screenshots\\dashboard_snapshot.html")
    assert str(plan.gallery_dir).endswith("assets\\screenshots\\gallery")
    assert str(plan.real_world_dir).endswith("assets\\screenshots\\real_world")
    assert str(plan.story_dir).endswith("docs\\screenshots\\story_frames")
    assert str(plan.gif_path).endswith("docs\\gifs\\dashboard_walkthrough.gif")


def test_export_dashboard_html(tmp_path, synthetic_dataset):
    output = export_dashboard_html(tmp_path / "snapshot.html", dataset=synthetic_dataset)
    assert output.exists()
    assert "<html" in output.read_text(encoding="utf-8", errors="ignore").lower()


def test_export_dashboard_html_accepts_configure_callback(tmp_path, synthetic_dataset):
    called = {"value": False}

    def configure(controller):
        called["value"] = controller._explorer is not None

    output = export_dashboard_html(tmp_path / "configured.html", dataset=synthetic_dataset, configure=configure)

    assert output.exists()
    assert called["value"]


def test_feature_gallery_captures_define_all_expected_views():
    captures = feature_gallery_captures("C:/tmp/lumen-xarray-lab")
    assert [capture.filename for capture in captures] == [
        "01_overview.png",
        "02_line_chart.png",
        "03_spatial_plot.png",
        "04_data_table.png",
        "05_statistics.png",
        "06_compare.png",
        "07_coverage.png",
        "08_source_query.png",
        "09_pseudo_sql.png",
        "10_time_analysis.png",
        "11_dataset_info.png",
        "12_query_planning.png",
        "13_multifile_loading.png",
        "14_transform_rolling_mean.png",
        "15_transform_anomaly.png",
        "16_transform_resample.png",
        "17_transform_climatology.png",
        "18_transform_spatial_mean.png",
        "19_transform_zonal_mean.png",
        "20_geoviews_map.png",
        "21_curvilinear_cf_metadata.png",
    ]


def test_write_capture_manifest(tmp_path):
    plan = build_capture_plan(tmp_path)
    manifest = write_capture_manifest(plan, screenshot_mode="html-only", notes=["ok"])
    assert manifest.exists()
    text = manifest.read_text(encoding="utf-8")
    assert "html-only" in text


def test_real_world_gallery_captures_define_expected_views():
    captures = real_world_gallery_captures("C:/tmp/lumen-xarray-lab")
    assert [capture.filename for capture in captures] == [
        "01_ersstv5_overview.png",
        "02_ersstv5_time_analysis.png",
        "03_ersstv5_dataset_info.png",
        "04_ersstv5_query_planning.png",
    ]


def test_make_gif_from_frames_normalizes_different_sizes(tmp_path):
    wide = tmp_path / "wide.png"
    tall = tmp_path / "tall.png"
    target = tmp_path / "out.gif"

    imageio.imwrite(wide, np.full((120, 240, 3), 32, dtype=np.uint8))
    imageio.imwrite(tall, np.full((240, 120, 3), 196, dtype=np.uint8))

    result = make_gif_from_frames([wide, tall], target, duration=0.2)

    assert result.exists()
    assert result.stat().st_size > 0
