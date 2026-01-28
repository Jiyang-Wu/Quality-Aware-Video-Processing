# Take two inputs: one reference frame and one target sample, and run VMAF to ensure acceptatble perceptual quality upon compression)
# Ensure that target sample and reference video share same resoluiton, pixel format, and FPS
from __future__ import annotations

import json
import subprocess
from pathlib import Path

def execute_vmaf(reference_path: Path, distorted_path: Path, out_dir: Path, video_name: str, crf_val: str):
    log_path = out_dir.resolve() / f"{video_name}_crf_{crf_val}.json"
    
    argv = [
        "ffmpeg",
        # Input url
        "-i", str(distorted_path.resolve()),
        "-i", str(reference_path.resolve()),
        # Output options
        "-lavfi", f"libvmaf=log_path={log_path}:log_fmt=json",
        "-f", "null", "-"
    ]
    print(argv)
    proc = subprocess.run(
        argv,
        text=True,
        capture_output=True,
        check=False
    )
    if proc.returncode != 0:
        print(proc.stderr)
        raise RuntimeError("vmaf generation failed")



def run_vmaf(parent_dir: Path, out_dir: Path, video_name: str, distorted_crfs: list):
    video_dir = parent_dir.resolve()
    reference_path = video_dir / f"{video_name}_10_reference.mp4"
    for crf_val in distorted_crfs:
        distorted = video_dir / f"{video_name}_{crf_val}_distorted.mp4"
        execute_vmaf(reference_path, distorted, out_dir, video_name, crf_val) 

def analyze_vmaf(vmaf_dir: Path, video_name: str, distorted_crfs: list):
    crf_vmaf_vals = dict()
    vmaf_base = vmaf_dir.resolve() 
    for distorted_crf_val in distorted_crfs:
        with open(vmaf_base / f"{video_name}_crf_{distorted_crf_val}.json") as f:
            crf_report = json.load(f) 
            crf_vmaf_vals[int(distorted_crf_val)] = float(crf_report["pooled_metrics"]["vmaf"]["mean"])
    return crf_vmaf_vals

def parse_bitrates(clips_dir: Path, video_name: str, distorted_crfs: list):
    bitrates = dict()
    clips_base = clips_dir.resolve()
    for distorted_crf_val in distorted_crfs:
        clip_path = clips_base / f"{video_name}_{distorted_crf_val}_distorted.mp4"
        probe_cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "format=duration",
            "-of", "json",
            str(clip_path),
        ]

        proc = subprocess.run(
            probe_cmd,
            text=True,
            capture_output=True,
            check=False,
        )

        if proc.returncode != 0:
            raise RuntimeError(f"ffprobe failed on {clip_path}:\n{proc.stderr}")

        try:
            data = json.loads(proc.stdout)
            duration = float(data["format"]["duration"])
        except (KeyError, ValueError, json.JSONDecodeError):
            raise RuntimeError(f"Failed to parse duration for {clip_path}")

        if duration <= 0:
            raise RuntimeError(f"Invalid duration for {clip_path}")

        size_bytes = clip_path.stat().st_size
        bitrate_kbps = (size_bytes * 8) / duration / 1000.0

        bitrates[distorted_crf_val] = int(bitrate_kbps)
    return bitrates