from __future__ import annotations

import panel as pn

from .explorer import ExplorerView
from .plots import (
    build_coordinate_table,
    build_dimension_table,
    build_preview_table,
    build_runtime_table,
    build_schema_table,
)
from .state import DashboardState
from .widgets import (
    build_capture_help,
    build_header,
    build_hero,
    build_metric_row,
    build_sidebar_card,
    build_summary,
)


def build_main_pane(state: DashboardState) -> pn.viewable.Viewable:
    explorer = ExplorerView(state=state)
    paper_styles = {
        "border-radius": "12px",
        "box-shadow": "0 1px 2px rgba(15, 23, 42, 0.06), 0 8px 24px rgba(15, 23, 42, 0.06)",
        "background": "#ffffff",
        "border": "1px solid #d9e1ea",
    }
    return pn.Column(
        build_hero(state),
        build_metric_row(state),
        pn.Row(
            pn.Card(
                build_header(state),
                title="Session",
                collapsed=False,
                sizing_mode="stretch_width",
                css_classes=["lxl-paper-card"],
                styles=paper_styles,
            ),
            pn.Card(
                build_summary(state),
                title="Dataset Summary",
                collapsed=False,
                sizing_mode="stretch_width",
                css_classes=["lxl-paper-card"],
                styles=paper_styles,
            ),
            sizing_mode="stretch_width",
        ),
        explorer,
        pn.Tabs(
            ("Sample Preview", build_preview_table(state)),
            ("Schema", build_schema_table(state)),
            ("Dimensions", build_dimension_table(state)),
            ("Coordinates", build_coordinate_table(state)),
            ("Runtime", build_runtime_table(state)),
        ),
        sizing_mode="stretch_width",
    )


def build_sidebar(state: DashboardState) -> list[pn.viewable.Viewable]:
    commands = pn.pane.Markdown(
        "\n".join(
            [
                "### Quick Commands",
                "`panel serve examples/dashboard_app.py --show`",
                "`python scripts/download_demo_data.py`",
                "`python scripts/make_screenshots.py`",
                "`python scripts/make_gif.py`",
            ]
        ),
        css_classes=["lxl-card-markdown"],
    )
    notes = pn.pane.Markdown(
        "\n".join(
            [
                "### Notes",
                "- The dashboard prefers a sibling upstream `lumen` checkout when available.",
                "- Screenshot capture is optional and requires Playwright.",
                "- GIF generation is optional and requires imageio.",
            ]
        ),
        css_classes=["lxl-card-markdown"],
    )
    return [
        build_sidebar_card("Workflow", commands),
        build_sidebar_card("Export", build_capture_help()),
        build_sidebar_card("Runtime Notes", notes),
    ]
