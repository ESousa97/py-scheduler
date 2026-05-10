from __future__ import annotations

import structlog
from prometheus_client import Counter, Histogram, start_http_server

from py_scheduler.models import SchedulerConfig

logger = structlog.get_logger(__name__)

# Métricas globais (registro único do prometheus_client).
JOB_FAILURES_TOTAL = Counter(
    "py_scheduler_job_failures_total",
    "Total de falhas finais por job (após esgotar retentativas).",
    ("job_id", "job_name"),
)

JOB_EXECUTION_SECONDS = Histogram(
    "py_scheduler_job_execution_seconds",
    "Duração de cada tentativa de execução, em segundos.",
    ("job_id", "job_name"),
    buckets=(
        0.001,
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        30.0,
        60.0,
    ),
)


def observe_attempt_duration_ms(
    *, job_id: str, job_name: str, duration_ms: int
) -> None:
    seconds = max(duration_ms, 0) / 1000.0
    JOB_EXECUTION_SECONDS.labels(job_id, job_name).observe(seconds)


def inc_terminal_failure(*, job_id: str, job_name: str) -> None:
    JOB_FAILURES_TOTAL.labels(job_id, job_name).inc()


def start_metrics_server(cfg: SchedulerConfig) -> None:
    if not cfg.metrics_enabled:
        logger.info("metrics_disabled")
        return
    start_http_server(cfg.metrics_port, addr=cfg.metrics_host)
    logger.info(
        "metrics_server_started",
        host=cfg.metrics_host,
        port=cfg.metrics_port,
    )
