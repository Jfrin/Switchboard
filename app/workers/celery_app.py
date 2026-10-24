from celery import Celery
from celery.signals import setup_logging

from app.config import get_settings

settings = get_settings()

celery_app = Celery("switchboard", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_acks_late=True, task_reject_on_worker_lost=True)
celery_app.autodiscover_tasks(["app.workers"])


@setup_logging.connect
def _configure_logging(**_kwargs) -> None:
    """Replace Celery's own log setup so worker logs use the same format as the API."""
    from app.logging_config import configure_logging

    configure_logging()
