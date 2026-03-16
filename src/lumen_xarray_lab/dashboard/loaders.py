from __future__ import annotations

from pathlib import Path

import xarray as xr

from ..datasets import load_demo_dataset
from .state import DashboardState


def load_demo_state() -> DashboardState:
    dataset = load_demo_dataset()
    return DashboardState.from_dataset(dataset)


def load_state_from_uri(uri: str, **source_kwargs) -> DashboardState:
    return DashboardState.from_uri(uri, **source_kwargs)


def resolve_state(dataset: xr.Dataset | None = None, uri: str | None = None, **source_kwargs) -> DashboardState:
    if dataset is not None:
        return DashboardState.from_dataset(dataset, **source_kwargs)
    if uri:
        return load_state_from_uri(uri, **source_kwargs)
    return load_demo_state()


def infer_uri_from_argv(argv: list[str]) -> str | None:
    if len(argv) < 2:
        return None
    candidate = Path(argv[1])
    return str(candidate) if candidate.exists() else None
