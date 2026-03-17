from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lumen_xarray_lab.benchmark_utils import benchmark_context, write_benchmark_report
from lumen_xarray_lab.datasets import LabXarraySourceAdapter, bundled_sample_paths


def main() -> None:
    samples = bundled_sample_paths()
    single_path = samples["air_temperature"]
    multi_path = samples["multi_air_temperature"]

    started = time.perf_counter()
    single_source = LabXarraySourceAdapter(uri=str(single_path))
    single_tables = single_source.get_tables()
    single_seconds = time.perf_counter() - started
    single_source.close()

    started = time.perf_counter()
    multi_source = LabXarraySourceAdapter(uri=str(multi_path))
    multi_tables = multi_source.get_tables()
    multi_seconds = time.perf_counter() - started
    multi_source.close()

    report = write_benchmark_report(
        "multifile_loading",
        {
            **benchmark_context("python benchmarks/multifile_loading.py"),
            "single_path": str(single_path),
            "multi_path": str(multi_path),
            "single_open_seconds": round(single_seconds, 4),
            "multi_open_seconds": round(multi_seconds, 4),
            "single_tables": single_tables,
            "multi_tables": multi_tables,
            "multifile_note": "Multi-file loading tries open_mfdataset first and falls back to manual combine_by_coords/concat when needed.",
        },
        ROOT / "benchmarks" / "results",
    )
    print(f"single_open_seconds: {single_seconds:.4f}")
    print(f"multi_open_seconds: {multi_seconds:.4f}")
    print(f"report: {report}")


if __name__ == "__main__":
    main()
