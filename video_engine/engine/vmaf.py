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