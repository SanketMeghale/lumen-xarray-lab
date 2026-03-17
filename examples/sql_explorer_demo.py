from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lumen_xarray_lab.datasets import load_demo_dataset
from lumen_xarray_lab.sql_source import ExperimentalSQLSource


def get_status() -> dict[str, object]:
    dataset = load_demo_dataset("air_temperature")
    source = ExperimentalSQLSource(dataset=dataset, max_rows=500)
    query = 'SELECT lat, AVG("air") AS mean_air FROM "air" GROUP BY lat ORDER BY lat'
    result = source.execute(query)
    status = source.status()
    status.update(
        {
            "query": query,
            "result_columns": list(result.columns),
            "result_rows": len(result),
        }
    )
    dataset.close()
    return status


def main() -> None:
    status = get_status()
    for key, value in status.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
