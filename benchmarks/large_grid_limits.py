from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lumen_xarray_lab.benchmark_utils import (
    benchmark_context,
    estimate_dataframe_bytes,
    estimate_flattened_rows,
    format_bytes,
    write_benchmark_report,
)


def main() -> None:
    sizes = {"time": 365, "lat": 721, "lon": 1440}
    rows = estimate_flattened_rows(sizes)
    columns = len(sizes) + 1
    bytes_estimate = estimate_dataframe_bytes(rows, columns)
    report = write_benchmark_report(
        "large_grid_limits",
        {
            **benchmark_context("python benchmarks/large_grid_limits.py"),
            "sizes": sizes,
            "large_grid_rows": rows,
            "large_grid_estimated_bytes": bytes_estimate,
            "large_grid_estimated_human": format_bytes(bytes_estimate),
        },
        ROOT / "benchmarks" / "results",
    )
    print(f"large_grid_rows: {rows}")
    print(f"large_grid_estimated_mb: {bytes_estimate / 1024 ** 2:.2f}")
    print(f"large_grid_estimated_human: {format_bytes(bytes_estimate)}")
    print(f"report: {report}")


if __name__ == "__main__":
    main()
