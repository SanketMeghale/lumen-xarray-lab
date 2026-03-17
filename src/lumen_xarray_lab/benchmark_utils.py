from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import sys
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


def benchmark_context(command: str | None = None) -> dict[str, object]:
    context: dict[str, object] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "cpu_count": os.cpu_count(),
    }
    if command is not None:
        context["command"] = command
    try:
        import psutil  # type: ignore
    except ImportError:
        return context
    context["memory_gb"] = round(psutil.virtual_memory().total / 1024 ** 3, 2)
    return context


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
