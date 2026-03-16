from __future__ import annotations

import panel as pn
import xarray as xr

from .loaders import resolve_state
from .panes import build_main_pane


def create_dashboard(dataset: xr.Dataset | None = None, uri: str | None = None) -> pn.template.FastListTemplate:
    pn.extension("tabulator")
    state = resolve_state(dataset=dataset, uri=uri)
    template = pn.template.FastListTemplate(
        title="lumen-xarray-lab",
        main=[build_main_pane(state)],
    )
    return template
