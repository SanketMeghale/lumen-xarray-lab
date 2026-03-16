from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def synthetic_dataset() -> xr.Dataset:
    return xr.Dataset(
        data_vars={
            "temperature": (
                ("time", "lat", "lon"),
                np.array(
                    [
                        [[1.0, 2.0], [3.0, 4.0]],
                        [[5.0, 6.0], [7.0, 8.0]],
                    ]
                ),
            )
        },
        coords={
            "time": np.array(["2024-01-01", "2024-01-02"], dtype="datetime64[ns]"),
            "lat": np.array([10.0, 20.0]),
            "lon": np.array([70.0, 80.0]),
        },
    )
