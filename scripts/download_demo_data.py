from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lumen_xarray_lab.datasets import save_demo_dataset


def main() -> None:
    target = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else ROOT / "assets" / "sample_data" / "air_temperature.nc"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    save_demo_dataset(target)
    print(f"saved: {target}")


if __name__ == "__main__":
    main()
