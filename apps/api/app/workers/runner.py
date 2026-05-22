"""CLI entrypoint for the ARQ worker."""

from arq import run_worker as arq_run_worker

from app.workers.settings import WorkerSettings


def run_worker() -> None:
    arq_run_worker(WorkerSettings)


if __name__ == "__main__":
    run_worker()
