from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lumen_xarray_lab.cf import detect_coordinates
from lumen_xarray_lab.datasets import build_source, load_demo_dataset


def build_report() -> dict[str, object]:
    dataset = load_demo_dataset()
    source = build_source(dataset=dataset, filterable_coords=["time", "lat", "lon"], max_rows=10000)
    table = source.get_tables()[0]
    preview = source.get(table, time="2013-01-01").head(5)
    report = {
        "table": table,
        "coordinate_map": detect_coordinates(dataset),
        "preview_columns": list(preview.columns),
        "preview_rows": len(preview),
    }
    if hasattr(source, "close"):
        source.close()
    dataset.close()
    return report


def main() -> None:
    report = build_report()
    for key, value in report.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
