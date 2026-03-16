from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping


def estimate_flattened_rows(sizes: Mapping[str, int]) -> int:
    rows = 1
    for size in sizes.values():
        rows *= int(size)
    return rows


def estimate_dataframe_bytes(rows: int, columns: int, bytes_per_value: int = 8) -> int:
    return int(rows) * int(columns) * int(bytes_per_value)


def estimate_row_explosion(source_rows: int, flattened_rows: int) -> float:
    if int(source_rows) <= 0:
        return 0.0
    return round(int(flattened_rows) / int(source_rows), 4)


def format_bytes(num_bytes: int) -> str:
    value = float(num_bytes)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{num_bytes} B"


def write_benchmark_report(
    name: str,
    metrics: Mapping[str, object],
    output_dir: str | Path | None = None,
) -> Path:
    directory = Path(output_dir) if output_dir is not None else Path("benchmarks") / "results"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{name}.json"
    target.write_text(json.dumps(dict(metrics), indent=2), encoding="utf-8")
    return target
