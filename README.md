# Quality-Aware Video Processing Engine

This repository implements a **quality-aware video encoding pipeline** that empirically explores rate–distortion tradeoffs using CRF sweeps and VMAF, and produces structured artifacts and reports explaining encoding decisions.

---

## Repository Structure

```text
.
├── README.md
│
├── v/                          # Raw input videos
│
│
├── assets/                     # Sample generated artifacts (checked in for reference)
│   └── {video_name}/
│       ├── clips/              # Encoded videos (reference + CRF candidates)
│       └── vmaf_reports/       # VMAF JSON outputs (one per CRF)
│
└── video-engine-subprocess/    # Executable video processing engine
    ├── cli.py                  # User-facing CLI (entry point)
    │
    └── engine/                 # Core pipeline implementation
        ├── pipeline.py         # Orchestrates the full processing flow
        ├── generator.py        # Reference + candidate video generation (FFmpeg)
        ├── vmaf.py             # VMAF execution and result parsing
        └── __pycache__/        # Python bytecode
```

## Steps to run

inside repo parent directory (/Quality-Aware-Video-Processing)

```text

docker run --rm -p 6379:6379 redis:7

celery -A video_engine.celery_app worker -l INFO

python3 -m video_engine.cli run --input v/bunny60.mp4 --out assets --policy balanced --resolution 1280:720 --fps 30 --crfs 18,20,22,24 --video_name bunny60

```