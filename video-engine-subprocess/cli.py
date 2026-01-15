#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from engine.pipeline import run_phase


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="video_engine",
        description="Quality-aware video encoding engine",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Run Phase 1 pipeline on a single rung (e.g., 720p).")
    run.add_argument("--input", type=Path, help="Input video file (e.g., input.mp4)")
    run.add_argument("--out", type=Path, required=True, help="Output directory")
    run.add_argument("--policy", choices=["quality", "balanced", "bandwidth"], default="balanced")
    run.add_argument("--rung", default="1280x720", help='Target resolution like "1280x720"')
    run.add_argument("--fps", type=float, default=30.0, help="Normalize fps for reference & candidates")
    run.add_argument("--crfs", default="18,20,22,24", help="Comma-separated CRF sweep")
    run.add_argument("--preset", default="slow", help="x264 preset")
    run.add_argument("--timeout-sec", type=int, default=1800, help="Per-ffmpeg command timeout seconds")

    analyze = sub.add_parser("analyze", help="Probe input and output analysis.json")
    analyze.add_argument("--input", type=Path)
    analyze.add_argument("--out", type=Path, required=True)

    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.cmd == "run":
        crfs = [int(x.strip()) for x in args.crfs.split(",") if x.strip()]
        run_phase(
            input_path=args.input,
            out_dir=args.out,
            policy_name=args.policy,
            rung=args.rung,
            fps=args.fps,
            crfs=crfs,
            preset=args.preset,
            timeout_sec=args.timeout_sec,
        )
        return 0

    if args.cmd == "analyze":
        from engine.pipeline import analyze_only
        analyze_only(args.input, args.out)
        return 0

    raise RuntimeError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
