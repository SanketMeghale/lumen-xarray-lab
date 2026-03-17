from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lumen_xarray_lab.benchmark_utils import benchmark_context, write_benchmark_report
from lumen_xarray_lab.datasets import load_demo_dataset
from lumen_xarray_lab.transforms import apply_transform


def main() -> None:
    dataset = load_demo_dataset("ersstv5")
    array = dataset["sst"]
    coord_map = {"time": "time", "latitude": "lat", "longitude": "lon", "vertical": None}

    timings: dict[str, float] = {}
    configs = {
        "rolling_mean": {"transform": "rolling mean", "window": 12},
        "anomaly": {"transform": "anomaly"},
        "resample": {"transform": "resample", "resample_rule": "QS-DEC"},
        "climatology": {"transform": "climatology"},
        "spatial_mean": {"transform": "spatial mean"},
        "zonal_mean": {"transform": "zonal mean"},
    }

    for name, config in configs.items():
        started = time.perf_counter()
        result = apply_transform(array, coord_map, aggregation="mean", **config)
        result.array.load()
        timings[name] = round(time.perf_counter() - started, 4)

    report = write_benchmark_report(
        "transform_timings",
        {
            **benchmark_context("python benchmarks/transform_timings.py"),
            "dataset": "ersstv5",
            "timings_seconds": timings,
        },
        ROOT / "benchmarks" / "results",
    )
    dataset.close()
    for name, seconds in timings.items():
        print(f"{name}: {seconds:.4f}")
    print(f"report: {report}")


if __name__ == "__main__":
    main()
