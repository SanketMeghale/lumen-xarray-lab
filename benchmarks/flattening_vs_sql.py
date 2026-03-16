from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lumen_xarray_lab.benchmark_utils import (
    estimate_dataframe_bytes,
    estimate_flattened_rows,
    estimate_row_explosion,
    format_bytes,
    write_benchmark_report,
)


def main() -> None:
    sizes = {"time": 2920, "lat": 25, "lon": 53}
    rows = estimate_flattened_rows(sizes)
    columns = len(sizes) + 1
    bytes_estimate = estimate_dataframe_bytes(rows, columns)
    metrics = {
        "sizes": sizes,
        "flattened_rows": rows,
        "estimated_dataframe_bytes": bytes_estimate,
        "estimated_dataframe_human": format_bytes(bytes_estimate),
        "row_explosion_vs_single_row_source": estimate_row_explosion(1, rows),
        "sql_note": "SQL comparison is a placeholder until the prototype is implemented.",
    }
    report = write_benchmark_report("flattening_vs_sql", metrics, ROOT / "benchmarks" / "results")
    print(f"flattened_rows: {rows}")
    print(f"estimated_dataframe_bytes: {bytes_estimate}")
    print(f"estimated_dataframe_human: {metrics['estimated_dataframe_human']}")
    print(f"report: {report}")
    print("sql_note: SQL comparison is a placeholder until the prototype is implemented.")


if __name__ == "__main__":
    main()
