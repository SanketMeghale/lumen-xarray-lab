from __future__ import annotations

from pathlib import Path

import xarray as xr

from ..datasets import load_demo_dataset
from .state import DashboardState


def load_demo_state() -> DashboardState:
    dataset = load_demo_dataset()
    return DashboardState.from_dataset(dataset)


def load_state_from_uri(uri: str) -> DashboardState:
    dataset = xr.open_dataset(uri)
    return DashboardState.from_dataset(dataset, uri=uri)


def resolve_state(dataset: xr.Dataset | None = None, uri: str | None = None) -> DashboardState:
    if dataset is not None:
        return DashboardState.from_dataset(dataset)
    if uri:
        return load_state_from_uri(uri)
    return load_demo_state()


def infer_uri_from_argv(argv: list[str]) -> str | None:
    if len(argv) < 2:
        return None
    candidate = Path(argv[1])
    return str(candidate) if candidate.exists() else None
