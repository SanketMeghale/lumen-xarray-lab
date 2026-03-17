from __future__ import annotations

from pathlib import Path
import tempfile
from urllib.parse import urlparse

import panel as pn
import xarray as xr

from ..datasets import bundled_sample_paths
from .loaders import resolve_state
from .panes import build_main_pane, build_sidebar
from .state import DashboardState
from .widgets import build_sidebar_card

RAW_CSS = """
:root {
  --lxl-primary: #1976d2;
  --lxl-primary-dark: #1565c0;
  --lxl-primary-soft: #e3f2fd;
  --lxl-primary-soft-strong: #d6e9ff;
  --lxl-bg: #f5f7fb;
  --lxl-sidebar: #fafafa;
  --lxl-surface: #ffffff;
  --lxl-surface-alt: #f8fafc;
  --lxl-border: #d9e1ea;
  --lxl-border-strong: #c4cfdb;
  --lxl-text: #1f2937;
  --lxl-muted: #6b7280;
  --lxl-shadow: 0 1px 2px rgba(15, 23, 42, 0.06), 0 8px 24px rgba(15, 23, 42, 0.06);
}

body, .bk-root {
  background: var(--lxl-bg);
  color: var(--lxl-text);
  font-family: Roboto, "Helvetica Neue", Arial, sans-serif;
}

.bk-header {
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}

.bk-sidebar {
  background: var(--lxl-sidebar) !important;
  border-right: 1px solid var(--lxl-border);
}

.bk-main {
  background: var(--lxl-bg);
}

.bk-input,
.bk-input-group input,
.bk-input-group select,
.bk-slider-title,
.bk-root input[type="text"],
.bk-root select {
  border-radius: 8px !important;
  border-color: var(--lxl-border-strong) !important;
  color: var(--lxl-text) !important;
  box-shadow: none !important;
}

.bk-btn,
.bk-btn-group button {
  border-radius: 8px !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}

.bk-btn-primary {
  background: var(--lxl-primary) !important;
  border-color: var(--lxl-primary) !important;
}

.bk-btn-primary:hover,
.bk-btn-primary:focus {
  background: var(--lxl-primary-dark) !important;
  border-color: var(--lxl-primary-dark) !important;
}

.bk-btn-light,
.bk-btn-default,
.bk-btn-success {
  background: var(--lxl-surface) !important;
  border: 1px solid var(--lxl-border-strong) !important;
  color: var(--lxl-text) !important;
}

.bk-Tabs-header,
.bk-tabs-header {
  background: transparent !important;
  border-bottom: 1px solid var(--lxl-border) !important;
}

.bk-tab,
.bk-tabs-header .bk-tab {
  background: transparent !important;
  color: var(--lxl-muted) !important;
  border: 0 !important;
  border-bottom: 2px solid transparent !important;
  font-weight: 500 !important;
}

.bk-tab.bk-active,
.bk-tabs-header .bk-tab.bk-active {
  color: var(--lxl-primary) !important;
  border-bottom-color: var(--lxl-primary) !important;
}

.tabulator {
  border: 1px solid var(--lxl-border) !important;
  border-radius: 12px !important;
  overflow: hidden;
  background: var(--lxl-surface);
}

.tabulator .tabulator-header {
  background: var(--lxl-surface-alt) !important;
  border-bottom: 1px solid var(--lxl-border) !important;
}

.tabulator .tabulator-col,
.tabulator .tabulator-cell {
  border-right-color: var(--lxl-border) !important;
}

.tabulator .tabulator-row {
  background: var(--lxl-surface) !important;
  border-bottom-color: #eef2f7 !important;
}

.tabulator .tabulator-row.tabulator-selected {
  background: var(--lxl-primary-soft) !important;
}

.lxl-paper-card {
  background: var(--lxl-surface);
  border: 1px solid var(--lxl-border);
  border-radius: 12px;
  box-shadow: var(--lxl-shadow);
}

.lxl-paper-card .bk-Card-header,
.lxl-paper-card .card-header {
  border-bottom: 1px solid var(--lxl-border);
  background: var(--lxl-surface);
  color: var(--lxl-text);
}

.lxl-hero {
  position: relative;
  padding: 22px 24px 20px 24px;
  border-radius: 12px;
  background: var(--lxl-surface);
  border: 1px solid var(--lxl-border);
  box-shadow: var(--lxl-shadow);
  margin-bottom: 14px;
  overflow: hidden;
}

.lxl-hero::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  height: 4px;
  background: var(--lxl-primary);
}

.lxl-kicker {
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 11px;
  color: var(--lxl-primary);
  font-weight: 700;
  margin-bottom: 12px;
}

.lxl-title {
  margin: 0 0 10px 0;
  font-size: 30px;
  line-height: 1.15;
  color: var(--lxl-text);
}

.lxl-subtitle {
  margin: 0;
  max-width: 840px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--lxl-muted);
}

.lxl-chip-row {
  margin-top: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.lxl-chip {
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--lxl-primary-soft);
  border: 1px solid #bbdefb;
  color: var(--lxl-primary-dark);
  font-size: 12px;
  font-weight: 600;
}

.lxl-metric-card {
  min-height: 110px;
  padding: 18px;
  border-radius: 12px;
  background: var(--lxl-surface);
  border: 1px solid var(--lxl-border);
  box-shadow: var(--lxl-shadow);
}

.lxl-metric-title {
  color: var(--lxl-muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 10px;
}

.lxl-metric-value {
  color: var(--lxl-text);
  font-size: 26px;
  font-weight: 700;
  line-height: 1.1;
  margin-bottom: 10px;
}

.lxl-metric-detail {
  color: var(--lxl-muted);
  font-size: 13px;
  line-height: 1.5;
}

.lxl-card-markdown {
  padding: 4px 0;
  color: var(--lxl-muted);
  line-height: 1.55;
}

.lxl-explorer-section-title {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--lxl-muted);
  margin: 4px 0 10px 0;
}

.lxl-explorer-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.lxl-explorer-summary > div {
  padding: 14px 16px;
  border-radius: 10px;
  background: var(--lxl-surface-alt);
  border: 1px solid var(--lxl-border);
  border-left: 3px solid var(--lxl-primary);
}

.lxl-explorer-summary strong {
  display: block;
  margin-top: 6px;
  color: var(--lxl-text);
  font-size: 18px;
}

.lxl-explorer-label {
  color: var(--lxl-muted);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.lxl-explorer-rail .bk-Card,
.lxl-explorer-rail .bk-panel-models-layout-Card,
.lxl-selection-banner,
.lxl-field-grid {
  box-shadow: var(--lxl-shadow);
}

.lxl-selection-banner {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
  padding: 16px 18px;
  border-radius: 12px;
  background: var(--lxl-surface);
  border: 1px solid var(--lxl-border);
}

.lxl-selection-banner > div {
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--lxl-surface-alt);
  border: 1px solid var(--lxl-border);
  min-height: 68px;
}

.lxl-selection-banner strong {
  display: block;
  margin-top: 8px;
  color: var(--lxl-text);
  font-size: 16px;
  line-height: 1.35;
}

.lxl-field-grid {
  display: grid;
  gap: 14px;
  padding: 8px 0 2px 0;
  border: 1px solid var(--lxl-border);
  border-radius: 12px;
  background: var(--lxl-surface);
  padding: 14px;
}

.lxl-field-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}

.lxl-field-chip {
  min-width: 110px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--lxl-primary-soft);
  border: 1px solid #bbdefb;
}

.lxl-field-chip span,
.lxl-field-chip em,
.lxl-field-copy {
  color: var(--lxl-muted);
  font-size: 12px;
  font-style: normal;
}

.lxl-field-chip strong {
  display: block;
  margin: 6px 0 4px 0;
  color: var(--lxl-text);
  font-size: 15px;
}

.lxl-field-copy {
  margin-top: 8px;
  line-height: 1.5;
  color: var(--lxl-text);
}
"""


class DashboardController:
    def __init__(self, dataset: xr.Dataset | None = None, uri: str | None = None):
        self._state: DashboardState | None = None
        self._temp_upload_paths: list[Path] = []
        self._active_upload_path: Path | None = None
        self._repo_root = Path(__file__).resolve().parents[3]
        self._bundled_samples = bundled_sample_paths()

        self._path_input = pn.widgets.TextInput(
            name="Path or URI",
            value=uri or "",
            placeholder=r"C:\data\climate.nc or /path/to/store.zarr",
            sizing_mode="stretch_width",
        )
        self._format_select = pn.widgets.Select(
            name="Format",
            options=["auto", "netcdf", "zarr"],
            value="auto",
            sizing_mode="stretch_width",
        )
        self._load_path_button = pn.widgets.Button(
            name="Load Path",
            button_type="primary",
            sizing_mode="stretch_width",
        )
        self._load_demo_button = pn.widgets.Button(
            name="Load Demo",
            button_type="light",
            sizing_mode="stretch_width",
        )
        self._sample_select = pn.widgets.Select(
            name="Bundled sample",
            options={name: str(path) for name, path in self._bundled_samples.items()} or {"none": ""},
            value=(str(next(iter(self._bundled_samples.values()))) if self._bundled_samples else ""),
            sizing_mode="stretch_width",
        )
        self._load_sample_button = pn.widgets.Button(
            name="Load Sample",
            button_type="primary",
            sizing_mode="stretch_width",
            disabled=not bool(self._bundled_samples),
        )
        self._upload_input = pn.widgets.FileInput(
            name="Upload dataset",
            accept=".nc,.nc4,.netcdf,.h5,.hdf5",
            sizing_mode="stretch_width",
        )
        self._load_upload_button = pn.widgets.Button(
            name="Load Upload",
            button_type="success",
            sizing_mode="stretch_width",
        )
        self._loader_summary = pn.pane.Markdown(css_classes=["lxl-card-markdown"])
        self._loader_status = pn.pane.Markdown(css_classes=["lxl-card-markdown"])

        self._load_path_button.on_click(self._on_load_path)
        self._load_demo_button.on_click(self._on_load_demo)
        self._load_sample_button.on_click(self._on_load_sample)
        self._load_upload_button.on_click(self._on_load_upload)

        self._loader_card = build_sidebar_card(
            "Load Dataset",
            pn.Column(
                pn.pane.Markdown(
                    "\n".join(
                        [
                            "### Load From Path",
                            "Use a local file path, remote URI, or a `.zarr` directory path.",
                        ]
                    ),
                    css_classes=["lxl-card-markdown"],
                ),
                self._path_input,
                self._format_select,
                pn.Row(self._load_path_button, self._load_demo_button, sizing_mode="stretch_width"),
                pn.pane.Markdown(
                    "\n".join(
                        [
                            "### Bundled Samples",
                            "Use a saved local sample to test the explorer quickly.",
                        ]
                    ),
                    css_classes=["lxl-card-markdown"],
                ),
                self._sample_select,
                self._load_sample_button,
                pn.pane.Markdown(
                    "\n".join(
                        [
                            "### Upload File",
                            "Upload a single NetCDF/HDF file directly into the current session.",
                        ]
                    ),
                    css_classes=["lxl-card-markdown"],
                ),
                self._upload_input,
                self._load_upload_button,
                pn.pane.Markdown(
                    "`Note:` `.zarr` is directory-based, so load it via the path input above.",
                    css_classes=["lxl-card-markdown"],
                ),
                self._loader_summary,
                self._loader_status,
                sizing_mode="stretch_width",
            ),
        )

        self._sidebar = pn.Column(sizing_mode="stretch_width")
        self._main = pn.Column(sizing_mode="stretch_width")

        self.template = pn.template.FastListTemplate(
            title="lumen-xarray-lab",
            accent_base_color="#1976d2",
            header_background="#1976d2",
            sidebar=[self._sidebar],
            theme_toggle=False,
            main_max_width="1500px",
            main=[self._main],
        )

        if dataset is not None:
            self.load_dataset(dataset, source_label="in-memory dataset")
        elif uri is not None:
            self.load_from_uri(uri, source_label=f"path `{uri}`")
        else:
            self.load_demo()

    @property
    def state(self) -> DashboardState:
        if self._state is None:
            raise ValueError("Dashboard state has not been initialized.")
        return self._state

    def _source_kwargs(self) -> dict[str, str]:
        if self._format_select.value == "auto":
            return {}
        return {"dataset_format": self._format_select.value}

    def _is_remote_uri(self, candidate: str) -> bool:
        parsed = urlparse(candidate)
        return bool(parsed.scheme and parsed.scheme not in ("file",) and not (len(parsed.scheme) == 1 and candidate[1:2] == ":"))

    def _normalize_uri_candidate(self, candidate: str) -> str:
        if self._is_remote_uri(candidate) or candidate.startswith("file://"):
            return candidate
        path = Path(candidate).expanduser()
        if path.is_absolute():
            return str(path)
        repo_relative = (self._repo_root / path).resolve()
        if repo_relative.exists():
            return str(repo_relative)
        cwd_relative = (Path.cwd() / path).resolve()
        if cwd_relative.exists():
            return str(cwd_relative)
        return str(path)

    def _set_status(self, message: str) -> None:
        self._loader_status.object = message

    def _update_loader_summary(self, source_label: str) -> None:
        state = self.state
        dataset_title = state.dataset.attrs.get("title", state.table)
        self._loader_summary.object = "\n".join(
            [
                f"**Current dataset:** {dataset_title}",
                f"**Loaded from:** {source_label}",
                f"**Tables:** {', '.join(state.tables)}",
                f"**Runtime:** `{state.runtime_source}`",
            ]
        )

    def _refresh_layout(self, source_label: str) -> None:
        self._main.objects = [build_main_pane(self.state)]
        self._sidebar.objects = [self._loader_card, *build_sidebar(self.state)]
        self._update_loader_summary(source_label)

    def _cleanup_temp_uploads(self, keep_path: Path | None = None) -> None:
        remaining: list[Path] = []
        for path in self._temp_upload_paths:
            if keep_path is not None and path == keep_path:
                remaining.append(path)
                continue
            try:
                path.unlink(missing_ok=True)
            except OSError:
                remaining.append(path)
        self._temp_upload_paths = remaining

    def _swap_state(
        self,
        next_state: DashboardState,
        source_label: str,
        status_message: str,
        active_upload_path: Path | None = None,
    ) -> None:
        previous_state = self._state
        self._state = next_state
        self._active_upload_path = active_upload_path
        self._refresh_layout(source_label)
        self._set_status(status_message)
        if previous_state is not None:
            previous_state.close()
        self._cleanup_temp_uploads(keep_path=self._active_upload_path)

    def load_demo(self) -> None:
        next_state = resolve_state()
        self._swap_state(
            next_state,
            source_label="built-in demo dataset",
            status_message="**Loaded demo dataset.**",
        )

    def load_dataset(self, dataset: xr.Dataset, source_label: str = "in-memory dataset") -> None:
        next_state = resolve_state(dataset=dataset, **self._source_kwargs())
        self._swap_state(
            next_state,
            source_label=source_label,
            status_message=f"**Loaded {source_label}.**",
        )

    def load_from_uri(self, uri: str, source_label: str | None = None) -> None:
        next_state = resolve_state(uri=uri, **self._source_kwargs())
        self._path_input.value = uri
        label = source_label or f"path `{uri}`"
        self._swap_state(
            next_state,
            source_label=label,
            status_message=f"**Loaded dataset from `{uri}`.**",
        )

    def load_from_upload(self, filename: str, value: bytes | bytearray | memoryview) -> None:
        suffix = "".join(Path(filename).suffixes) or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            payload = bytes(value)
            tmp.write(payload)
            target = Path(tmp.name)
        self._temp_upload_paths.append(target)
        next_state = resolve_state(uri=str(target), **self._source_kwargs())
        self._path_input.value = str(target)
        self._swap_state(
            next_state,
            source_label=f"uploaded file `{filename}`",
            status_message=f"**Loaded uploaded file `{filename}`.**",
            active_upload_path=target,
        )

    def _on_load_path(self, event=None) -> None:
        candidate = self._path_input.value.strip()
        if not candidate:
            self._set_status("**Load failed:** enter a dataset path or URI first.")
            return
        resolved = self._normalize_uri_candidate(candidate)
        if not self._is_remote_uri(resolved) and not resolved.startswith("file://") and not Path(resolved).exists():
            self._set_status(f"**Load failed:** `{resolved}` does not exist.")
            return
        try:
            self._set_status(f"**Loading:** opening `{resolved}` ...")
            self.load_from_uri(resolved)
        except Exception as exc:
            self._set_status(f"**Load failed:** `{resolved}` could not be opened. `{exc}`")

    def _on_load_demo(self, event=None) -> None:
        try:
            self._set_status("**Loading:** opening bundled demo dataset ...")
            self.load_demo()
        except Exception as exc:  # pragma: no cover - defensive UI path
            self._set_status(f"**Load failed:** demo dataset could not be loaded. `{exc}`")

    def _on_load_sample(self, event=None) -> None:
        if not self._sample_select.value:
            self._set_status("**Load failed:** no bundled sample is available.")
            return
        try:
            self._set_status(f"**Loading:** opening bundled sample `{Path(self._sample_select.value).name}` ...")
            self.load_from_uri(self._sample_select.value, source_label=f"bundled sample `{Path(self._sample_select.value).name}`")
        except Exception as exc:
            self._set_status(
                f"**Load failed:** bundled sample `{Path(self._sample_select.value).name}` could not be opened. `{exc}`"
            )

    def _on_load_upload(self, event=None) -> None:
        if not self._upload_input.value or not self._upload_input.filename:
            self._set_status("**Load failed:** choose a file to upload first.")
            return
        try:
            self._set_status(f"**Loading:** opening uploaded file `{self._upload_input.filename}` ...")
            self.load_from_upload(self._upload_input.filename, self._upload_input.value)
        except Exception as exc:
            self._set_status(
                f"**Load failed:** uploaded file `{self._upload_input.filename}` could not be opened. `{exc}`"
            )


def create_dashboard(dataset: xr.Dataset | None = None, uri: str | None = None) -> pn.template.FastListTemplate:
    pn.extension("tabulator", raw_css=[RAW_CSS])
    controller = DashboardController(dataset=dataset, uri=uri)
    controller.template._dashboard_controller = controller
    return controller.template
