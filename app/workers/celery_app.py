from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery("switchboard", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_acks_late=True, task_reject_on_worker_lost=True)
celery_app.autodiscover_tasks(["app.workers"])
