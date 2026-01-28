from .celery_app import app
from .engine.pipeline import run, run_abr
from pathlib import Path
from typing import Callable, Optional


@app.task(bind = True, name = "video_engine.process_job_task")
def process_job_task(self, spec: dict) -> dict:
    spec["video_input_path"] = Path(spec["video_input_path"])
    spec["out_asset_dir"] = Path(spec["out_asset_dir"])

    def progress_callback(step: str):
        progress = {"step": step}
        self.update_state(state = "PROGRESS", meta = progress)

    res = None
    progress_callback("Starting")
    if spec["abr"]:
       res = run_abr(spec, progress_callback) 
    else:
        res = run(spec, progress_callback)
    progress_callback("Done")
    return res