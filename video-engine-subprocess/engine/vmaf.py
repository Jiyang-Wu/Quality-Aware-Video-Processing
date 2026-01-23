# Take two inputs: one reference frame and one target sample, and run VMAF to ensure acceptatble perceptual quality upon compression)
# Ensure that target sample and reference video share same resoluiton, pixel format, and FPS
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple, Optional


candidate_crfs = ["18", "20", "22", "24", "44"]
def execute_vmaf(reference_path: Path, candidate_path: Path, out_dir: Path, video_name: str, crf_val: str):
    log_path = out_dir.resolve() / f"{video_name}" / f"{video_name}_crf_{crf_val}.json"
    
    argv = [
        "ffmpeg",
        # Input url
        "-i", candidate_path.resolve(),
        "-i", reference_path.resolve(),
        # Output options
        "-lavfi", f"libvmaf=log_path={log_path}:log_fmt=json",
        "-f", "null -"
    ]
    proc = subprocess.run(
        argv,
        text=True,
        capture_output=True,
        check=False
    )
    if proc.returncode != 0:
        print(proc.stderr)
        raise RuntimeError("reference generation failed")



def run_vmaf(parent_dir: Path, out_dir: Path, video_name: str):
    video_dir = (parent_dir / video_name).resolve()
    reference_path = video_dir / f"{video_name}_10_reference.mp4"
    for crf_val in candidate_crfs:
        candidate = video_dir / f"{video_name}_{crf_val}_candidate.mp4"
        execute_vmaf(reference_path, candidate, out_dir, video_name, crf_val) 