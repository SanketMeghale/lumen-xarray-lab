from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lumen_xarray_lab.dashboard.export_flow import (
    build_capture_plan,
    capture_feature_gallery,
    capture_dashboard_story_frames,
    capture_dashboard_png,
    ensure_capture_dirs,
    export_dashboard_html,
    write_capture_manifest,
)


def run_capture(uri: str | None = None, html_only: bool = False) -> dict[str, str]:
    plan = build_capture_plan(ROOT)
    ensure_capture_dirs(plan)
    export_dashboard_html(plan.html_path, uri=uri)
    notes = ["Static HTML snapshot exported successfully."]
    screenshot_mode = "html-only"

    if not html_only:
        try:
            capture_dashboard_png(plan.html_path, plan.desktop_png, width=1600, height=1080)
            capture_dashboard_png(plan.html_path, plan.mobile_png, width=430, height=1200)
            capture_dashboard_story_frames(plan.html_path, plan.story_dir)
            capture_feature_gallery(ROOT)
            screenshot_mode = "playwright"
            notes.append("Captured desktop, mobile, story-frame, and feature-gallery screenshots with Playwright.")
        except Exception as exc:
            notes.append(f"PNG capture skipped: {exc}")

    write_capture_manifest(plan, screenshot_mode=screenshot_mode, notes=notes)
    return {
        "html": str(plan.html_path),
        "desktop_png": str(plan.desktop_png),
        "mobile_png": str(plan.mobile_png),
        "gallery_dir": str(plan.gallery_dir),
        "story_dir": str(plan.story_dir),
        "manifest": str(plan.manifest_path),
        "gif_target": str(plan.gif_path),
        "mode": screenshot_mode,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export dashboard HTML and optional screenshots.")
    parser.add_argument("--uri", default=None, help="Optional dataset path to load instead of the demo dataset.")
    parser.add_argument("--html-only", action="store_true", help="Skip browser screenshot capture.")
    args = parser.parse_args()
    result = run_capture(uri=args.uri, html_only=args.html_only)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
