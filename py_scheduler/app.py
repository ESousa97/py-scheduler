from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers import SchedulerNotRunningError
from apscheduler.schedulers.blocking import BlockingScheduler
import structlog
from tenacity import RetryCallState, retry, stop_after_attempt, wait_exponential

from py_scheduler.loader import load_scheduler_config
from py_scheduler.models import JobConfig, SchedulerConfig
from py_scheduler.registry import JobRegistry
from py_scheduler.webhooks import WebhookNotifier

structured_logger = structlog.get_logger(__name__)


def _duration_ms(started_at: float) -> int:
    return round((time.perf_counter() - started_at) * 1000)


def _with_retry(
    job: JobConfig,
    func: Callable[..., object],
    *,
    webhook_notifier: WebhookNotifier,
) -> Callable[..., object]:
    retry_config = job.retry
    job_logger = structured_logger.bind(job_id=job.id, job_name=job.name)
    attempt_started_at: dict[int, float] = {}
    current_attempt_number = {"value": 1}

    def _before_attempt(retry_state: RetryCallState) -> None:
        current_attempt_number["value"] = retry_state.attempt_number
        attempt_started_at[retry_state.attempt_number] = time.perf_counter()

    def _after_attempt(retry_state: RetryCallState) -> None:
        if retry_state.outcome is None or not retry_state.outcome.failed:
            return
        attempt_number = retry_state.attempt_number
        started_at = attempt_started_at.pop(attempt_number, retry_state.start_time)
        exception = retry_state.outcome.exception()
        status = "failed" if attempt_number >= retry_config.attempts else "retry"
        log_method = job_logger.error if status == "failed" else job_logger.warning
        log_method(
            "job_execution",
            status=status,
            duration_ms=_duration_ms(started_at),
            attempt_number=attempt_number,
            error_type=type(exception).__name__ if exception is not None else None,
            error_message=str(exception) if exception is not None else None,
        )
        if status == "failed":
            err_text = str(exception) if exception is not None else None
            webhook_notifier.notify_job_failed(job.name, err_text)

    def _run_job() -> object:
        started_at = time.perf_counter()
        attempt_number = current_attempt_number["value"]
        result = func()
        attempt_started_at.pop(attempt_number, None)
        job_logger.info(
            "job_execution",
            status="success",
            duration_ms=_duration_ms(started_at),
            attempt_number=attempt_number,
        )
        if job.notify_on_success:
            webhook_notifier.notify_job_succeeded(job.name)
        return result

    return retry(
        reraise=True,
        stop=stop_after_attempt(retry_config.attempts),
        wait=wait_exponential(
            multiplier=retry_config.wait_multiplier_seconds,
            min=retry_config.wait_min_seconds,
            max=retry_config.wait_max_seconds,
        ),
        before=_before_attempt,
        after=_after_attempt,
    )(_run_job)


class SchedulerApp:
    """Monta APScheduler a partir de registry + arquivo YAML."""

    __slots__ = ("_registry", "_config_path")

    def __init__(self, registry: JobRegistry, config_path: str | Path) -> None:
        self._registry = registry
        self._config_path = Path(config_path)

    def load_config(self) -> SchedulerConfig:
        return load_scheduler_config(self._config_path)

    def build_scheduler(self, config: SchedulerConfig | None = None) -> BlockingScheduler:
        cfg = config if config is not None else self.load_config()
        executors = {"default": ThreadPoolExecutor(max_workers=4)}
        job_defaults: dict[str, object] = {"coalesce": True, "max_instances": 1}
        scheduler = BlockingScheduler(
            executors=executors,
            job_defaults=job_defaults,
        )
        notifier = WebhookNotifier.from_config(cfg.webhook)
        for job in cfg.jobs:
            func = self._registry.get(job.name)
            retrying_func = _with_retry(job, func, webhook_notifier=notifier)
            kwargs = job.interval.to_apscheduler_kwargs()
            scheduler.add_job(
                retrying_func,
                trigger="interval",
                id=job.id,
                replace_existing=True,
                **kwargs,
            )
        return scheduler

    def run_forever(self) -> None:
        """Inicia o scheduler até interrupção; encerra com shutdown(wait=True)."""
        scheduler: BlockingScheduler | None = None
        try:
            scheduler = self.build_scheduler()
            n = len(scheduler.get_jobs())
            structured_logger.info("scheduler_started", job_count=n)
            scheduler.start()
        except KeyboardInterrupt:
            structured_logger.info("shutdown_requested")
        finally:
            if scheduler is not None:
                try:
                    scheduler.shutdown(wait=True)
                    structured_logger.info("scheduler_stopped")
                except SchedulerNotRunningError:
                    structured_logger.debug("scheduler_shutdown_skipped")
