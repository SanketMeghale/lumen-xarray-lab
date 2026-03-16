from __future__ import annotations

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lumen_xarray_lab.ai_hooks import build_cli_example, build_upload_preview
from lumen_xarray_lab.datasets import save_demo_dataset


def run_demo() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_demo_dataset(Path(tmpdir) / "air_temperature.nc")
        preview = build_upload_preview(str(path))
        preview["cli_example"] = build_cli_example(str(path))
        return preview


def main() -> None:
    preview = run_demo()
    for key, value in preview.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
