from __future__ import annotations

import subprocess
from pathlib import Path

# create a sample reference for the input video under target resolution
candidate_crfs = ["18", "20", "22", "24", "44"]

def exec_ffmpeg(input_path: Path, 
                output_dir: Path, 
                crf_value: str, 
                clip_type: str,
                ffmpeg_filter: str):

    in_file_name = input_path.stem
    argv = [
        "ffmpeg",
        # Global Options
        "-y",
        # Input url
        "-i", str(input_path.resolve()),
        # Output options
        "-vf", ffmpeg_filter,
        "-c:v", "libx264",
        "-crf", crf_value,
        "-preset", "veryslow",
        "-g", "60",
        "-keyint_min", "60",
        "-sc_threshold", "0",
        "-an",
        # Output url
        output_dir / f"{in_file_name}_{crf_value}_{clip_type}.mp4"
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


def generate_reference(input_path: Path, 
                       output_dir: Path, 
                       ffmpeg_filter: str):
    exec_ffmpeg(input_path, output_dir, "10", "reference", ffmpeg_filter)


def generate_distorted(input_path: Path, 
                       output_dir: Path, 
                       ffmpeg_filter: str,
                       crf_vals=candidate_crfs):
    for crf_val in crf_vals:
        exec_ffmpeg(input_path, output_dir, crf_val, "distorted", ffmpeg_filter)
