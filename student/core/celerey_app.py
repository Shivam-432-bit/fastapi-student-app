from celery import Celery

celery_app = Celery(
    "student",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# Autodiscover tasks from workers.tasks module
celery_app.autodiscover_tasks(["student.workers"])