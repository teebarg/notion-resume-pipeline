from arq.connections import RedisSettings

from app.config import get_settings
from app.workers import tasks

_settings = get_settings()


class WorkerSettings:
    functions = [tasks.export_resume_task]
    on_startup = tasks.on_startup
    on_shutdown = tasks.on_shutdown
    redis_settings = RedisSettings.from_dsn(_settings.redis_url)
    queue_name = _settings.redis_job_queue
    max_jobs = 10
    job_timeout = 300
