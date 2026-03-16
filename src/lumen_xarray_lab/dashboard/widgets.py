from __future__ import annotations

import panel as pn

from .state import DashboardState


def _metric_card(title: str, value: str, detail: str) -> pn.pane.HTML:
    return pn.pane.HTML(
        f"""
        <div class="lxl-metric-card">
          <div class="lxl-metric-title">{title}</div>
          <div class="lxl-metric-value">{value}</div>
          <div class="lxl-metric-detail">{detail}</div>
        </div>
        """,
        sizing_mode="stretch_width",
    )


def build_hero(state: DashboardState) -> pn.pane.HTML:
    title = state.dataset.attrs.get("title", state.table)
    chips = [
        state.runtime_source,
        f"table:{state.table}",
        f"coords:{sum(1 for value in state.coord_map.values() if value is not None)}",
        f"dims:{len(state.dimension_info)}",
    ]
    chip_html = "".join(f'<span class="lxl-chip">{chip}</span>' for chip in chips)
    return pn.pane.HTML(
        f"""
        <section class="lxl-hero">
          <div class="lxl-kicker">Companion Dashboard</div>
          <h1 class="lxl-title">{title}</h1>
          <p class="lxl-subtitle">
            A proposal-oriented view of how xarray datasets can be interpreted,
            enriched, and presented for Lumen workflows.
          </p>
          <div class="lxl-chip-row">{chip_html}</div>
        </section>
        """,
        sizing_mode="stretch_width",
    )


def build_metric_row(state: DashboardState) -> pn.Row:
    dims_label = ", ".join(state.dimension_info) if state.dimension_info else "none"
    coords_label = ", ".join(
        f"{role}:{name}" for role, name in state.coord_map.items() if name is not None
    ) or "none"
    return pn.Row(
        _metric_card("Tables", str(len(state.tables)), ", ".join(state.tables)),
        _metric_card("Preview Rows", str(len(state.preview)), "sampled current table view"),
        _metric_card("Dimensions", str(len(state.dimension_info)), dims_label),
        _metric_card("Coordinates", str(len(state.coord_metadata)), coords_label),
        sizing_mode="stretch_width",
    )


def build_header(state: DashboardState) -> pn.pane.Markdown:
    mode = state.runtime_details.get("mode", state.runtime_source)
    source_class = state.runtime_details.get("source_class", "unknown")
    return pn.pane.Markdown(
        "\n".join(
            [
                "# lumen-xarray-lab",
                f"Runtime source: `{state.runtime_source}`",
                f"Runtime mode: `{mode}`",
                f"Source class: `{source_class}`",
                f"Active table: `{state.table}`",
            ]
        )
    )


def build_summary(state: DashboardState) -> pn.pane.Markdown:
    dims = ", ".join(f"{k}={v}" for k, v in state.dataset.sizes.items())
    coords = ", ".join(f"{key}: {value}" for key, value in state.coord_map.items())
    dimension_keys = ", ".join(state.dimension_info) if state.dimension_info else "none"
    tables = ", ".join(state.tables)
    description = state.metadata.get("description", state.table)
    title = state.dataset.attrs.get("title", "untitled dataset")
    return pn.pane.Markdown(
        "\n".join(
            [
                f"**Dataset title:** {title}",
                f"**Description:** {description}",
                f"**Tables:** {tables}",
                f"**Dimensions:** {dims}",
                f"**Detected coordinates:** {coords}",
                f"**Queryable dimensions:** {dimension_keys}",
                f"**Rows previewed:** {len(state.preview)}",
            ]
        ),
        css_classes=["lxl-card-markdown"],
    )


def build_capture_help() -> pn.pane.Markdown:
    return pn.pane.Markdown(
        "\n".join(
            [
                "### Capture Flow",
                "`python scripts/make_screenshots.py` exports a static HTML dashboard snapshot.",
                "If Playwright is installed, it also captures desktop and mobile PNG screenshots.",
                "`python scripts/make_gif.py` combines saved PNG frames into a GIF.",
            ]
        ),
        css_classes=["lxl-card-markdown"],
    )


def build_sidebar_card(title: str, body: pn.viewable.Viewable) -> pn.Card:
    return pn.Card(
        body,
        title=title,
        collapsed=False,
        sizing_mode="stretch_width",
        styles={
            "border-radius": "18px",
            "box-shadow": "0 18px 45px rgba(15, 23, 42, 0.08)",
        },
    )
