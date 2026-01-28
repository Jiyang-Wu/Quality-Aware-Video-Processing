#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from .engine.pipeline import run 
from time import sleep
from celery.result import AsyncResult
from .celery_app import app
from .tasks import process_job_task


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="video_engine",
        description="Quality-aware video encoding engine",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # run --input ../v/bunny30.mp4 --out ../assets --policy balanced --resolution 1280:720 --fps 30 --crfs 18,20,22,24 --video_name bunny30
    run = sub.add_parser("run", help="Run Phase 1 pipeline on a single rung (e.g., 720p).")
    run.add_argument("--input", type=Path, help="Input video file (e.g., input.mp4)")
    run.add_argument("--out", type=Path, required=True, help="Output directory")
    run.add_argument("--codec", choices=["HEVC", "H264", "AV1"], default="H264", help="chooce the desired codec")
    run.add_argument("--policy", choices=["quality", "balanced", "bandwidth"], default="balanced")
    run.add_argument("--resolution", default="1280:720", help='Target resolution like "720p"')
    run.add_argument("--fps", type=int, default=30, help="Normalize fps for reference & candidates")
    run.add_argument("--crfs", type=str, default="18,20,22,24", help="Comma-separated CRF sweep")
    run.add_argument("--video_name", type=str)
    run.add_argument("--abr", type=bool, default=False, help="enabling ABR or not")

    analyze = sub.add_parser("analyze", help="Probe input and output analysis.json")
    analyze.add_argument("--input", type=Path)
    analyze.add_argument("--out", type=Path, required=True)

    generator = sub.add_parser("generator", help="Generate reference or distorted video")
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
                    codec: str,
                    fps: int,
                    crfs: str,
                    video_name: str,
                    abr: bool):
    job_spec = dict()
    job_spec["video_input_path"] = str(input.resolve())
    job_spec["out_asset_dir"] = str(out.resolve())
    job_spec["policy"] = policy
    job_spec["codec"] = codec
    job_spec["resolution"] = resolution
    job_spec["fps"] = fps
    job_spec["crfs"] = crfs
    job_spec["video_name"] = video_name
    job_spec["ffmpeg_filter"] = f"scale={resolution}:flags=lanczos,fps={str(fps)},format=yuv420p"
    job_spec["abr"] = abr
    return job_spec

def main() -> int:
    args = parse_args()

    if args.cmd == "run":
        from .tasks import process_job_task
        job_spec = create_job_spec(args.input,
                                args.out,
                                args.policy,
                                args.resolution,
                                args.codec,
                                args.fps,
                                args.crfs,
                                args.video_name,
                                args.abr)
        res = process_job_task.delay(job_spec)
        print("task_id:", res.id)
        last = "Starting Task"
        while True:
            r = AsyncResult(res.id, app=app)
            state = r.state
            info = r.info

            step = ""
            if isinstance(info, dict) and "step" in info:
                step = info["step"]

            line = f"{state}"
            if step:
                line += f" | {step}"

            if line != last:
                print(line)
                last = line

            if state in ("SUCCESS", "FAILURE", "REVOKED"):
                break

            sleep(0.5)

        if r.successful:
            output = r.get()
            if isinstance(output, dict):
                print("final video clip url: ", r.get()["final_video_url"])
        else:
            print("Failed: ", r.result())
        return 0

    if args.cmd == "analyze":
        from engine.pipeline import analyze_only
        analyze_only(args.input, args.out)
        return 0

    raise RuntimeError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
