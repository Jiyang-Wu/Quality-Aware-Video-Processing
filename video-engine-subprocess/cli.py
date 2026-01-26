#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from engine.pipeline import run 


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
    run.add_argument("--resolution", default="1280:720", help='Target resolution like "720p"')
    run.add_argument("--fps", type=int, default=30, help="Normalize fps for reference & candidates")
    run.add_argument("--crfs", type=str, default="18,20,22,24", help="Comma-separated CRF sweep")
    run.add_argument("--video_name", type=str)

    analyze = sub.add_parser("analyze", help="Probe input and output analysis.json")
    analyze.add_argument("--input", type=Path)
    analyze.add_argument("--out", type=Path, required=True)

    generator = sub.add_parser("generator", help="Generate reference video")
    generator.add_argument("--type", type=str)
    generator.add_argument("--input", type=Path)
    generator.add_argument("--out", type=Path)

    vmaf = sub.add_parser("vmaf", help = "Run VMAF comparison")
    vmaf.add_argument("--parent_dir", type=Path)
    vmaf.add_argument("--out_dir", type=Path)
    vmaf.add_argument("--video_name", type=str)

    return p.parse_args()


# TODO: write job spec to redis queue
def create_job_spec(input: Path,
                    out: Path,
                    policy: str,
                    resolution: str,
                    fps: int,
                    crfs: str,
                    video_name: str):
    job_spec = dict()
    job_spec["video_input_path"] = input
    job_spec["out_asset_dir"] = out
    job_spec["policy"] = policy
    job_spec["resolution"] = resolution
    job_spec["fps"] = fps
    job_spec["crfs"] = crfs
    job_spec["video_name"] = video_name
    job_spec["ffmpeg_filter"] = f"scale={resolution}:flags=lanczos,fps={str(fps)},format=yuv420p"
    return job_spec

def main() -> int:
    args = parse_args()

    if args.cmd == "run":
        job_spec = create_job_spec(args.input,
                                args.out, 
                                args.policy, 
                                args.resolution, 
                                args.fps, 
                                args.crfs, 
                                args.video_name)
        run(job_spec)
        return 0

    if args.cmd == "analyze":
        from engine.pipeline import analyze_only
        analyze_only(args.input, args.out)
        return 0

    if args.cmd == "generator":
        video_name = args.input.stem
        out_dir = args.out / f"{video_name}"
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        if args.type == "reference":
            from engine.generator import generate_reference
            print("reference generation")
            generate_reference(args.input, out_dir, "720p", 30)
        elif args.type == "distorted":
            from engine.generator import generate_distorted
            print("distorted generation")
            generate_distorted(args.input, out_dir, "720p", 30)
        return 0

    if args.cmd == "vmaf":
        from engine.vmaf import run_vmaf
        Path(args.out_dir).mkdir(parents=True, exist_ok=True)
        Path(args.out_dir / args.video_name).mkdir(parents=True, exist_ok=True)
        run_vmaf(args.parent_dir, args.out_dir, args.video_name)
        return 0


    raise RuntimeError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
