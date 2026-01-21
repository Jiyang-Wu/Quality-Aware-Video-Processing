from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# create a sample reference for the input video under target resolution
filters = {
            "720p" : 
            {
                "30": "scale=1280:720:flags=lanczos,fps=30,format=yuv420p"
            }
        }

def exec_ffmpeg(input_path: Path, output_dir: Path, target_res: str, target_FPS: int):
    in_file_name = input_path.stem
    argv = [
        "ffmpeg",
        # Global Options
        "-y",
        # Input url
        "-i", str(input_path.resolve()),
        # Output options
        "-vf", filters[target_res][str(target_FPS)],
        "-c:v", "libx264",
        "-crf", "10",
        "-preset", "veryslow",
        "-g", "60",
        "-keyint_min", "60",
        "-sc_threshold", "0",
        "-an",
        # Output url
        output_dir / f"{in_file_name}_reference.mp4"
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


def generate_reference(input_path: Path, output_dir: Path, target_res: str, target_FPS: int):
    exec_ffmpeg(input_path, output_dir, target_res, target_FPS)

