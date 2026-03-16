from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lumen_xarray_lab.dashboard.export_flow import build_capture_plan, make_gif_from_frames


def build_default_frames(root: Path) -> tuple[list[Path], Path]:
    plan = build_capture_plan(root)
    return [plan.desktop_png, plan.mobile_png], plan.gif_path


def run_gif(frames: list[Path], output: Path, duration: float) -> dict[str, str]:
    try:
        result = make_gif_from_frames(frames, output, duration=duration)
    except Exception as exc:
        return {
            "status": "skipped",
            "reason": str(exc),
        }
    return {
        "status": "created",
        "gif": str(result),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Combine saved dashboard screenshots into a GIF.")
    parser.add_argument("frames", nargs="*", help="Optional explicit frame paths.")
    parser.add_argument("--output", default=None, help="Optional output GIF path.")
    parser.add_argument("--duration", type=float, default=1.1, help="Seconds per frame.")
    args = parser.parse_args()

    if args.frames:
        frames = [Path(frame) for frame in args.frames]
        output = Path(args.output) if args.output else ROOT / "docs" / "gifs" / "custom_dashboard.gif"
    else:
        frames, output = build_default_frames(ROOT)
        if args.output:
            output = Path(args.output)

    result = run_gif(frames, output, duration=args.duration)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
