from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import tempfile
from typing import Callable, Iterable

import numpy as np
import xarray as xr

from .app import create_dashboard


@dataclass(frozen=True)
class CapturePlan:
    html_path: Path
    desktop_png: Path
    mobile_png: Path
    gallery_dir: Path
    story_dir: Path
    manifest_path: Path
    gif_path: Path

    def to_dict(self) -> dict[str, str]:
        return {key: str(value) for key, value in asdict(self).items()}


@dataclass(frozen=True)
class FeatureGalleryCapture:
    uri: str
    filename: str
    target_selector: str
    configure: Callable[[object], None] | None = None


def build_capture_plan(root: str | Path) -> CapturePlan:
    root = Path(root)
    return CapturePlan(
        html_path=root / "docs" / "screenshots" / "dashboard_snapshot.html",
        desktop_png=root / "assets" / "screenshots" / "dashboard_desktop.png",
        mobile_png=root / "assets" / "screenshots" / "dashboard_mobile.png",
        gallery_dir=root / "assets" / "screenshots" / "gallery",
        story_dir=root / "docs" / "screenshots" / "story_frames",
        manifest_path=root / "docs" / "screenshots" / "capture_manifest.json",
        gif_path=root / "docs" / "gifs" / "dashboard_walkthrough.gif",
    )


def ensure_capture_dirs(plan: CapturePlan) -> None:
    for path in (plan.html_path, plan.desktop_png, plan.mobile_png, plan.manifest_path, plan.gif_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    plan.gallery_dir.mkdir(parents=True, exist_ok=True)
    plan.story_dir.mkdir(parents=True, exist_ok=True)


def export_dashboard_html(
    output_path: str | Path,
    dataset: xr.Dataset | None = None,
    uri: str | None = None,
    configure: Callable[[object], None] | None = None,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    dashboard = create_dashboard(dataset=dataset, uri=uri)
    controller = getattr(dashboard, "_dashboard_controller", None)
    if configure is not None and controller is not None:
        configure(controller)
    dashboard.save(str(output), resources="inline")
    return output


def _as_file_url(path: str | Path) -> str:
    return Path(path).resolve().as_uri()


def _normalize_frame_shapes(images: list[np.ndarray]) -> list[np.ndarray]:
    if not images:
        return images

    normalized: list[np.ndarray] = []
    max_height = max(image.shape[0] for image in images)
    max_width = max(image.shape[1] for image in images)
    max_channels = max(image.shape[2] if image.ndim == 3 else 1 for image in images)

    for image in images:
        if image.ndim == 2:
            image = np.repeat(image[:, :, None], max_channels, axis=2)
        elif image.shape[2] != max_channels:
            if image.shape[2] == 1:
                image = np.repeat(image, max_channels, axis=2)
            elif image.shape[2] > max_channels:
                image = image[:, :, :max_channels]
            else:
                pad_channels = max_channels - image.shape[2]
                channel_pad = np.full(
                    (image.shape[0], image.shape[1], pad_channels),
                    255,
                    dtype=image.dtype,
                )
                image = np.concatenate([image, channel_pad], axis=2)

        canvas = np.full((max_height, max_width, max_channels), 255, dtype=image.dtype)
        offset_y = (max_height - image.shape[0]) // 2
        offset_x = (max_width - image.shape[1]) // 2
        canvas[offset_y : offset_y + image.shape[0], offset_x : offset_x + image.shape[1]] = image
        normalized.append(canvas)
    return normalized


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


def capture_dashboard_story_frames(
    html_path: str | Path,
    output_dir: str | Path,
    width: int = 1600,
    height: int = 1200,
    wait_ms: int = 1800,
) -> list[Path]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Story-frame capture requires 'playwright'. Install it and run "
            "'python -m playwright install chromium'."
        ) from exc

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    for existing in target_dir.glob("*.png"):
        existing.unlink()
    html_url = _as_file_url(html_path)
    sequence = [
        ("overview", None),
        ("data", "Data"),
        ("statistics", "Statistics"),
        ("source_query", "Source Query"),
        ("pseudo_sql", "Pseudo SQL"),
    ]
    clip = {"x": 40, "y": 190, "width": 1510, "height": 900}
    captured: list[Path] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(html_url, wait_until="networkidle")
        page.wait_for_timeout(wait_ms)

        for index, (slug, label) in enumerate(sequence, start=1):
            if label is not None:
                page.locator(f"text={label}").first.click()
                page.wait_for_timeout(600)
            target = target_dir / f"{index:02d}_{slug}.png"
            page.screenshot(path=str(target), clip=clip)
            captured.append(target)

        browser.close()
    return captured


def capture_gallery_png(
    html_path: str | Path,
    output_path: str | Path,
    target_selector: str,
    width: int = 1600,
    height: int = 1800,
    wait_ms: int = 2200,
) -> Path:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Gallery capture requires 'playwright'. Install it and run "
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
        locator = page.locator(target_selector).first
        locator.scroll_into_view_if_needed()
        page.wait_for_timeout(400)
        locator.screenshot(path=str(target))
        browser.close()
    return target


def _set_numeric_filter(controller: object, name: str, value: tuple[float, float]) -> None:
    widget = controller._explorer.filter_widgets.get(name)
    if widget is not None:
        widget.value = value


def _set_first_datetime(controller: object, name: str = "time") -> None:
    widget = controller._explorer.filter_widgets.get(name)
    if widget is not None and hasattr(widget, "start"):
        widget.value = (widget.start, widget.start)


def _configure_line_chart(controller: object) -> None:
    explorer = controller._explorer
    _set_first_datetime(controller)
    _set_numeric_filter(controller, "lat", (70.0, 70.0))
    if "lon" in explorer._x.options:
        explorer._x.value = "lon"
    explorer._limit.value = 60
    explorer._output_tabs.active = 0


def _configure_spatial_plot(controller: object) -> None:
    explorer = controller._explorer
    _set_first_datetime(controller)
    explorer._chart_type.value = "spatial"
    explorer._limit.value = 250
    explorer._output_tabs.active = 0


def _configure_filtered_query(controller: object, tab_index: int) -> None:
    explorer = controller._explorer
    _set_numeric_filter(controller, "lon", (220.0, 300.0))
    explorer._limit.value = 120
    explorer._output_tabs.active = tab_index


def _configure_compare(controller: object) -> None:
    explorer = controller._explorer
    explorer._compare_table.value = "humidity"
    explorer._output_tabs.active = 3


def feature_gallery_captures(root: str | Path) -> list[FeatureGalleryCapture]:
    root = Path(root)
    samples = root / "assets" / "sample_data"
    return [
        FeatureGalleryCapture(
            uri=str(samples / "air_temperature.nc"),
            filename="01_overview.png",
            target_selector=".lxl-explorer-root",
        ),
        FeatureGalleryCapture(
            uri=str(samples / "air_temperature.nc"),
            filename="02_line_chart.png",
            target_selector=".lxl-explorer-output-card",
            configure=_configure_line_chart,
        ),
        FeatureGalleryCapture(
            uri=str(samples / "air_temperature.nc"),
            filename="03_spatial_plot.png",
            target_selector=".lxl-explorer-output-card",
            configure=_configure_spatial_plot,
        ),
        FeatureGalleryCapture(
            uri=str(samples / "air_temperature.nc"),
            filename="04_data_table.png",
            target_selector=".lxl-explorer-output-card",
            configure=lambda controller: _configure_filtered_query(controller, 1),
        ),
        FeatureGalleryCapture(
            uri=str(samples / "air_temperature.nc"),
            filename="05_statistics.png",
            target_selector=".lxl-explorer-output-card",
            configure=lambda controller: _configure_filtered_query(controller, 2),
        ),
        FeatureGalleryCapture(
            uri=str(samples / "compare_weather.nc"),
            filename="06_compare.png",
            target_selector=".lxl-explorer-output-card",
            configure=_configure_compare,
        ),
        FeatureGalleryCapture(
            uri=str(samples / "air_temperature.nc"),
            filename="07_coverage.png",
            target_selector=".lxl-explorer-output-card",
            configure=lambda controller: _configure_filtered_query(controller, 4),
        ),
        FeatureGalleryCapture(
            uri=str(samples / "air_temperature.nc"),
            filename="08_source_query.png",
            target_selector=".lxl-explorer-output-card",
            configure=lambda controller: _configure_filtered_query(controller, 5),
        ),
        FeatureGalleryCapture(
            uri=str(samples / "air_temperature.nc"),
            filename="09_pseudo_sql.png",
            target_selector=".lxl-explorer-output-card",
            configure=lambda controller: _configure_filtered_query(controller, 6),
        ),
    ]


def capture_feature_gallery(root: str | Path) -> list[Path]:
    root = Path(root)
    plan = build_capture_plan(root)
    ensure_capture_dirs(plan)
    for existing in plan.gallery_dir.glob("*.png"):
        existing.unlink()

    rendered: list[Path] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        for capture in feature_gallery_captures(root):
            html_path = tmp_root / capture.filename.replace(".png", ".html")
            export_dashboard_html(html_path, uri=capture.uri, configure=capture.configure)
            rendered.append(
                capture_gallery_png(
                    html_path,
                    plan.gallery_dir / capture.filename,
                    target_selector=capture.target_selector,
                )
            )
    return rendered


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
    images = _normalize_frame_shapes([imageio.imread(frame) for frame in frames])
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
