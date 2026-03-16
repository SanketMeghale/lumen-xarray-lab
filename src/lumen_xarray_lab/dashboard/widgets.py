from __future__ import annotations

import panel as pn

from .state import DashboardState


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
        )
    )
