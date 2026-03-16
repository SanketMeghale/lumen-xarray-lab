from __future__ import annotations

import panel as pn

from .plots import (
    build_coordinate_table,
    build_dimension_table,
    build_preview_table,
    build_runtime_table,
    build_schema_table,
)
from .state import DashboardState
from .widgets import build_header, build_summary


def build_main_pane(state: DashboardState) -> pn.viewable.Viewable:
    return pn.Column(
        build_header(state),
        build_summary(state),
        pn.Tabs(
            ("Preview", build_preview_table(state)),
            ("Schema", build_schema_table(state)),
            ("Dimensions", build_dimension_table(state)),
            ("Coordinates", build_coordinate_table(state)),
            ("Runtime", build_runtime_table(state)),
        ),
        sizing_mode="stretch_width",
    )
