from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lumen_xarray_lab.cf import detect_coordinates
from lumen_xarray_lab.datasets import (
    build_source,
    load_demo_dataset,
    resolve_runtime_source_info,
    resolve_runtime_source_name,
)


def collect_summary() -> dict[str, object]:
    dataset = load_demo_dataset()
    source = build_source(dataset=dataset, filterable_coords=["time", "lat", "lon"])
    table = source.get_tables()[0]
    summary = {
        "runtime_source": resolve_runtime_source_name(),
        "runtime_details": resolve_runtime_source_info().to_dict(),
        "tables": source.get_tables(),
        "table": table,
        "schema_keys": list(source.get_schema(table).keys()),
        "coordinates": detect_coordinates(dataset),
    }
    if hasattr(source, "close"):
        source.close()
    dataset.close()
    return summary


def main() -> None:
    summary = collect_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
