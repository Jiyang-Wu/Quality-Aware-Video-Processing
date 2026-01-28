from .celery_app import app
from .engine.pipeline import run
from pathlib import Path

@app.task(name = "video_engine.process_job_task")
def process_job_task(spec: dict) -> dict:
    spec["video_input_path"] = Path(spec["video_input_path"])
    spec["out_asset_dir"] = Path(spec["out_asset_dir"])
    return run(job_spec=spec)