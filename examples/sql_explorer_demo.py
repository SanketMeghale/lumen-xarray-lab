from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lumen_xarray_lab.sql_source import ExperimentalSQLSource


def get_status() -> dict[str, object]:
    return ExperimentalSQLSource().status()


def main() -> None:
    status = get_status()
    for key, value in status.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
