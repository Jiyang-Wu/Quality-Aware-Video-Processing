from celery import Celery

app = Celery(
    "video_engine",
    broker = "redis://localhost:6379/0",
    backend = "redis://localhost:6379/1",
    include = ["video_engine.tasks"]
)

app.conf.update(
    task_serializer = "json",
    accept_content = ["json"],
    result_serializer = "json",
    task_track_started = True,
    worker_prefetch_multiplier = 1,
    task_acks_late = True,
)