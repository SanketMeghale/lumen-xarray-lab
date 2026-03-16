from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lumen_xarray_lab.dashboard.app import create_dashboard
from lumen_xarray_lab.dashboard.loaders import infer_uri_from_argv


def build_app():
    return create_dashboard(uri=infer_uri_from_argv(sys.argv))


app = build_app()
app.servable()


if __name__ == "__main__":
    import panel as pn

    pn.serve(app, show=True)
