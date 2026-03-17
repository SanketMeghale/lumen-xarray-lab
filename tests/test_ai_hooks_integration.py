from __future__ import annotations

from pathlib import Path

from lumen_xarray_lab.ai_hooks import build_upload_preview
from lumen_xarray_lab.datasets import save_demo_dataset


def test_build_upload_preview(tmp_path):
    path = save_demo_dataset(Path(tmp_path) / "air_temperature.nc")
    preview = build_upload_preview(str(path))
    assert "tables" in preview
    assert preview["path"].endswith(".nc")
    assert preview["engine"] == "netcdf"
    assert preview["table"] == "air"
    assert "time" in preview["schema_keys"]
    assert preview["suggested_prompts"]
