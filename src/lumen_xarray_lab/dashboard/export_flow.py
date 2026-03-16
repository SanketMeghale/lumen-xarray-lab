from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable

import xarray as xr

from .app import create_dashboard


@dataclass(frozen=True)
class CapturePlan:
    html_path: Path
    desktop_png: Path
    mobile_png: Path
    manifest_path: Path
    gif_path: Path

    def to_dict(self) -> dict[str, str]:
        return {key: str(value) for key, value in asdict(self).items()}


def build_capture_plan(root: str | Path) -> CapturePlan:
    root = Path(root)
    return CapturePlan(
        html_path=root / "docs" / "screenshots" / "dashboard_snapshot.html",
        desktop_png=root / "assets" / "screenshots" / "dashboard_desktop.png",
        mobile_png=root / "assets" / "screenshots" / "dashboard_mobile.png",
        manifest_path=root / "docs" / "screenshots" / "capture_manifest.json",
        gif_path=root / "docs" / "gifs" / "dashboard_walkthrough.gif",
    )


def ensure_capture_dirs(plan: CapturePlan) -> None:
    for path in (plan.html_path, plan.desktop_png, plan.mobile_png, plan.manifest_path, plan.gif_path):
        path.parent.mkdir(parents=True, exist_ok=True)


def export_dashboard_html(
    output_path: str | Path,
    dataset: xr.Dataset | None = None,
    uri: str | None = None,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    dashboard = create_dashboard(dataset=dataset, uri=uri)
    dashboard.save(str(output), resources="inline")
    return output


def _as_file_url(path: str | Path) -> str:
    return Path(path).resolve().as_uri()


def capture_dashboard_png(
    html_path: str | Path,
    output_path: str | Path,
    width: int = 1600,
    height: int = 1080,
    wait_ms: int = 1800,
) -> Path:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Screenshot capture requires 'playwright'. Install it and run "
            "'python -m playwright install chromium'."
        ) from exc

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    html_url = _as_file_url(html_path)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(html_url, wait_until="networkidle")
        page.wait_for_timeout(wait_ms)
        page.screenshot(path=str(target), full_page=True)
        browser.close()
    return target


def make_gif_from_frames(
    frame_paths: Iterable[str | Path],
    output_path: str | Path,
    duration: float = 1.0,
) -> Path:
    try:
        import imageio.v2 as imageio
    except ImportError as exc:
        raise RuntimeError(
            "GIF generation requires 'imageio'. Install it with the demo extras."
        ) from exc

    frames = [Path(frame) for frame in frame_paths if Path(frame).exists()]
    if not frames:
        raise ValueError("No existing frames were provided for GIF generation.")
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    images = [imageio.imread(frame) for frame in frames]
    imageio.mimsave(target, images, duration=duration, loop=0)
    return target


def write_capture_manifest(
    plan: CapturePlan,
    screenshot_mode: str,
    notes: list[str] | None = None,
) -> Path:
    payload = {
        "paths": plan.to_dict(),
        "screenshot_mode": screenshot_mode,
        "notes": notes or [],
    }
    plan.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    plan.manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return plan.manifest_path
