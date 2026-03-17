from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import xarray as xr

from lumen_xarray_lab.benchmark_utils import benchmark_context, write_benchmark_report
from lumen_xarray_lab.datasets import load_demo_dataset


def timed_open(path: Path) -> float:
    started = time.perf_counter()
    ds = xr.open_dataset(path)
    ds.load()
    ds.close()
    return time.perf_counter() - started


def main() -> None:
    dataset = load_demo_dataset()
    with tempfile.TemporaryDirectory() as tmpdir:
        nc_path = Path(tmpdir) / "air_temperature.nc"
        dataset.to_netcdf(nc_path)
        netcdf_seconds = timed_open(nc_path)
    dataset.close()
    report = write_benchmark_report(
        "netcdf_vs_zarr",
        {
            **benchmark_context("python benchmarks/netcdf_vs_zarr.py"),
            "netcdf_open_seconds": round(netcdf_seconds, 4),
            "zarr_available": False,
            "zarr_note": "Add Zarr timing once the environment is configured with zarr.",
        },
        ROOT / "benchmarks" / "results",
    )
    print(f"netcdf_open_seconds: {netcdf_seconds:.4f}")
    print(f"report: {report}")
    print("zarr_note: Add Zarr timing once the environment is configured with zarr.")


if __name__ == "__main__":
    main()
