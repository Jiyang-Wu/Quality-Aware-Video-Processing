from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from .generator import generate_distorted, generate_reference
from .vmaf import run_vmaf, analyze_vmaf, parse_bitrates

abr_res = ["1920:1080", "1280:720", "960:540", "640:360"]
def exec_ffprobe(input_path: Path):
    argv = [
        "ffprobe",
        "-hide_banner",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(input_path) 
    ]
    proc = subprocess.run(
        argv,
        text=True,
        capture_output=True,
        check=False
    )
    if proc.returncode != 0:
        raise RuntimeError("ffprobe failed")
    
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError("Failed to parse JSON output from ffprobe")

def parse_ratio(r: Optional[str]) -> Optional[float]:
    """Parse ffprobe ratio string like '30000/1001' into float."""
    if not r or r == "0/0":
        return None
    if "/" in r:
        num_s, den_s = r.split("/", 1)
        try:
            num = float(num_s)
            den = float(den_s)
            if den == 0:
                return None
            return num / den
        except ValueError:
            return None
    try:
        return float(r)
    except ValueError:
        return None

def analyze_only(in_path: Path, out_dir_path: Path):
    input_path = in_path.resolve()
    output_dir = out_dir_path.resolve()

    raw = exec_ffprobe(input_path)
    
    streams = raw.get("streams", [])
    fmt = raw.get("format", {}) or {}

    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    # Duration: prefer format.duration, else stream.duration
    duration_sec = None
    for cand in (fmt.get("duration"), (video or {}).get("duration"), (audio or {}).get("duration")):
        if cand is None:
            continue
        try:
            duration_sec = float(cand)
            break
        except (TypeError, ValueError):
            continue

    analysis: Dict[str, Any] = {
        "input_path": str(input_path),
        "container": {
            "format_name": fmt.get("format_name"),
            "format_long_name": fmt.get("format_long_name"),
            "size_bytes": int(fmt["size"]) if isinstance(fmt.get("size"), str) and fmt["size"].isdigit() else None,
            "bit_rate_bps": int(fmt["bit_rate"]) if isinstance(fmt.get("bit_rate"), str) and fmt["bit_rate"].isdigit() else None,
            "duration_sec": duration_sec,
        },
        "video": None,
        "audio": None,
        "notes": [],
    }

    # for video, key info would be:
    #   - FPS(avg_frame_rate or r_frame_rate)
    #   - bitrate (bit_rate) 
    if video:
        fps = 0.0
        avg = parse_ratio(video.get("avg_frame_rate"))
        r_frame_rate = parse_ratio(video.get("r_frame_rate"))
        if avg:
           fps = avg
        elif r_frame_rate:
           fps = r_frame_rate
           analysis["notes"].append("avg_frame_rate missing; input may be VFR or metadata incomplete.\n")

        if avg and r_frame_rate and abs(avg - r_frame_rate) / max(avg, r_frame_rate, 1e-9) > 0.10:
            analysis["notes"].append("avg_frame_rate and r_frame_rate differ notably; input may be VFR. Consider normalizing FPS for scoring.\n")

        v_bps = None
        br = video.get("bit_rate")
        if isinstance(br, str) and br.isdigit():
            v_bps = int(br)

        analysis["video"] = {
            "codec": video.get("codec_name") or video.get("codec_tag_string"),
            "profile": video.get("profile"),
            "width": video.get("width"),
            "height": video.get("height"),
            "pix_fmt": video.get("pix_fmt"),
            "fps": fps,
            "avg_frame_rate": video.get("avg_frame_rate"),
            "r_frame_rate": video.get("r_frame_rate"),
            "bit_rate_bps": v_bps,
            "time_base": video.get("time_base"),
            "color": {
                "color_range": video.get("color_range"),
                "color_space": video.get("color_space"),
                "color_transfer": video.get("color_transfer"),
                "color_primaries": video.get("color_primaries"),
            },
        }        
    else:
        analysis["notes"].append("No Video Stream\n")

    # for audio, key info would be:
    #   - sample rate (sample_rate)
    #   - channels (channels)
    if audio:
        sr = audio.get("sample_rate")
        sample_rate = int(sr) if isinstance(sr, str) else None
        ch = audio.get("channels")
        channels = int(ch) if isinstance(ch, int) else None

        analysis["audio"] = {
            "codec": audio.get("codec_name") or audio.get("codec_tag_string"),
            "profile": audio.get("profile"),
            "channels": channels,
            "channel_layout": audio.get("channel_layout"),
            "sample_rate_hz": sample_rate,
            "bit_rate_bps": int(audio["bit_rate"]) if isinstance(audio.get("bit_rate"), str) and audio["bit_rate"].isdigit() else None,
        }
    else:
        analysis["notes"].append("No Audio Stream\n")

    in_file_name = in_path.stem
    (out_dir_path / f"{in_file_name}_analysis.json").write_text(json.dumps(analysis, indent=2), encoding = "utf-8")

# Using modules to finish an cycle of generation
def run(job_spec: dict, progress_callback: Callable):

    video_input_path = job_spec["video_input_path"]
    out_asset_dir = job_spec["out_asset_dir"] 
    policy = job_spec["policy"] 
    resolution = job_spec["resolution"] 
    fps = job_spec["fps"] 
    crfs = job_spec["crfs"] 
    video_name = job_spec["video_name"] 
    ffmpeg_filter = job_spec["ffmpeg_filter"] 
    codec = job_spec["codec"]

    crf_vals=crfs.split(",")
    video_input_path_abs = video_input_path.resolve()
    out_asset_dir_abs = out_asset_dir.resolve()
    out_video_clips_abs = out_asset_dir_abs / video_name / "clips"
    out_video_vmaf_abs = out_asset_dir_abs / video_name / "vmaf_reports"
    Path(out_video_clips_abs).mkdir(parents=True, exist_ok=True)
    Path(out_video_vmaf_abs).mkdir(parents=True, exist_ok=True)

    # Generate Reference
    progress_callback("Generating reference")
    generate_reference(video_input_path_abs, out_video_clips_abs, ffmpeg_filter, codec)

    # Generate Distorted
    progress_callback("Generating distorted")
    generate_distorted(video_input_path_abs, out_video_clips_abs, ffmpeg_filter, codec, crf_vals)

    # Run VMAF
    progress_callback("Running VMAF comparison")
    run_vmaf(out_video_clips_abs, out_video_vmaf_abs, video_name, crf_vals)

    # Based on quality policy, select a good target
    vmaf_report = analyze_vmaf(out_video_vmaf_abs, video_name, crf_vals)
    print(vmaf_report)
    final_crf = 0
    if policy == "quality":
        print("examing quality candidates")
        max_vmaf = 0
        for crf, vmaf in vmaf_report.items():
            if vmaf > max_vmaf: 
                final_crf = crf
                max_vmaf = vmaf
    elif policy == "balanced":
        print("examing balanced candidates")
        for crf, vmaf in vmaf_report.items():
            if vmaf > 95 and crf > final_crf:
                final_crf = crf
    # elif policy_name == "bandwidth":
    #     for crf, vmaf in vmaf_report.items():
    print(final_crf)
    res = dict()
    res["final_crf"] = final_crf
    final_video_url = out_video_clips_abs / f"{video_name}_{str(final_crf)}_distorted.mp4"
    res["final_video_url"] = str(final_video_url)
    return res



def run_abr(job_spec: dict, progress_callback: Callable):

    video_input_path = job_spec["video_input_path"]
    out_asset_dir = job_spec["out_asset_dir"] 
    policy = job_spec["policy"] 
    fps = job_spec["fps"] 
    crfs = job_spec["crfs"] 
    video_name = job_spec["video_name"] 
    ffmpeg_filter = job_spec["ffmpeg_filter"] 
    codec = job_spec["codec"]

    crf_vals=crfs.split(",")
    video_input_path_abs = video_input_path.resolve()
    out_asset_dir_abs = out_asset_dir.resolve()

    ladder_candidates = []

    for res in abr_res:

        res_name = res.split(":")[1]
        out_video_clips_abs = out_asset_dir_abs / video_name / res_name / "clips"
        out_video_vmaf_abs = out_asset_dir_abs / video_name / res_name / "vmaf_reports"
        Path(out_video_clips_abs).mkdir(parents=True, exist_ok=True)
        Path(out_video_vmaf_abs).mkdir(parents=True, exist_ok=True)

        #ffmpeg_filter:  f"scale={resolution}:flags=lanczos,fps={str(fps)},format=yuv420p"
        ffmpeg_filter = f"scale={res}:flags=lanczos,fps={str(fps)},format=yuv420p"
        # Generate Reference
        progress_callback("Generating reference for " + res)
        generate_reference(video_input_path_abs, out_video_clips_abs, ffmpeg_filter, codec)

        # Generate Distorted
        progress_callback("Generating distorted")
        generate_distorted(video_input_path_abs, out_video_clips_abs, ffmpeg_filter, codec, crf_vals)

        # Run VMAF
        progress_callback("Running VMAF comparison")
        run_vmaf(out_video_clips_abs, out_video_vmaf_abs, video_name, crf_vals)

        # Based on quality policy, select a good target
        vmaf_report = analyze_vmaf(out_video_vmaf_abs, video_name, crf_vals)
        bitrates = parse_bitrates(out_video_clips_abs, video_name, crf_vals)

        print(vmaf_report)
        print(bitrates)

    return {"final_video_url": "haha"}

