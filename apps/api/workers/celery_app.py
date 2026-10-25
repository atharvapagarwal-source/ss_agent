"""
Celery application factory with Redis broker.
All background tasks import from this module to get the shared app instance.
"""
from celery import Celery
from config import settings

celery_app = Celery(
    "socialcoach",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "workers.tasks.newsjack_poller",
        "workers.tasks.dm_dispatcher",
        "workers.tasks.analytics_poller",
        "workers.tasks.scheduler",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,               # Re-queue on worker crash
    worker_prefetch_multiplier=1,      # Fair distribution across workers
    task_routes={
        "workers.tasks.dm_dispatcher.*": {"queue": "dm_queue"},
        "workers.tasks.analytics_poller.*": {"queue": "analytics_queue"},
        "workers.tasks.newsjack_poller.*": {"queue": "research_queue"},
        "workers.tasks.scheduler.*": {"queue": "default"},
    },
    task_default_queue="default",
)
