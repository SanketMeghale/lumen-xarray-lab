from __future__ import annotations

import panel as pn
import xarray as xr

from .loaders import resolve_state
from .panes import build_main_pane, build_sidebar

RAW_CSS = """
:root {
  --lxl-ink: #142321;
  --lxl-muted: #51656a;
  --lxl-accent: #117864;
  --lxl-accent-soft: #d9efe8;
  --lxl-warm: #cf7f29;
  --lxl-paper: #fbf7ef;
  --lxl-surface: rgba(255, 255, 255, 0.92);
}

body, .bk-root {
  background:
    radial-gradient(circle at top right, rgba(17, 120, 100, 0.12), transparent 28%),
    radial-gradient(circle at left center, rgba(207, 127, 41, 0.10), transparent 24%),
    linear-gradient(180deg, #f4efe3 0%, #fbf7ef 100%);
  color: var(--lxl-ink);
}

.lxl-hero {
  padding: 28px 30px;
  border-radius: 24px;
  background: linear-gradient(135deg, #163b38 0%, #117864 58%, #d88a33 100%);
  color: #fff8f0;
  box-shadow: 0 30px 60px rgba(17, 24, 39, 0.16);
  margin-bottom: 16px;
}

.lxl-kicker {
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 11px;
  opacity: 0.85;
  margin-bottom: 10px;
}

.lxl-title {
  margin: 0 0 10px 0;
  font-size: 34px;
  line-height: 1.1;
}

.lxl-subtitle {
  margin: 0;
  max-width: 760px;
  font-size: 15px;
  line-height: 1.6;
}

.lxl-chip-row {
  margin-top: 18px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.lxl-chip {
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(255, 248, 240, 0.14);
  border: 1px solid rgba(255, 248, 240, 0.2);
  font-size: 12px;
}

.lxl-metric-card {
  min-height: 120px;
  padding: 18px;
  border-radius: 20px;
  background: var(--lxl-surface);
  border: 1px solid rgba(20, 35, 33, 0.08);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
}

.lxl-metric-title {
  color: var(--lxl-muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 10px;
}

.lxl-metric-value {
  color: var(--lxl-ink);
  font-size: 28px;
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
}

.lxl-explorer-section-title {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--lxl-muted);
  margin: 4px 0 8px 0;
}

.lxl-explorer-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.lxl-explorer-summary > div {
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(17, 120, 100, 0.08);
  border: 1px solid rgba(17, 120, 100, 0.14);
}

.lxl-explorer-summary strong {
  display: block;
  margin-top: 6px;
  color: var(--lxl-ink);
  font-size: 18px;
}

.lxl-explorer-label {
  color: var(--lxl-muted);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
"""


def create_dashboard(dataset: xr.Dataset | None = None, uri: str | None = None) -> pn.template.FastListTemplate:
    pn.extension("tabulator", raw_css=[RAW_CSS])
    state = resolve_state(dataset=dataset, uri=uri)
    template = pn.template.FastListTemplate(
        title="lumen-xarray-lab",
        accent_base_color="#117864",
        header_background="#163b38",
        sidebar=build_sidebar(state),
        theme_toggle=False,
        main_max_width="1500px",
        main=[build_main_pane(state)],
    )
    return template
