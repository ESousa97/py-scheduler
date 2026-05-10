from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from py_scheduler.models import (
    JobConfig,
    SchedulerConfig,
    WebhookConfig,
    interval_from_mapping,
    retry_from_mapping,
)


def _parse_job(entry: dict[str, Any], index: int) -> JobConfig:
    job_id = entry.get("id")
    name = entry.get("name")
    interval_raw = entry.get("interval")
    retry_raw = entry.get("retry")
    if not isinstance(job_id, str) or not job_id.strip():
        raise ValueError(f"jobs[{index}].id deve ser uma string não vazia")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"jobs[{index}].name deve ser uma string não vazia")
    if not isinstance(interval_raw, dict):
        raise ValueError(f"jobs[{index}].interval deve ser um mapeamento")
    if retry_raw is not None and not isinstance(retry_raw, dict):
        raise ValueError(f"jobs[{index}].retry deve ser um mapeamento")
    interval = interval_from_mapping(cast(dict[str, Any], interval_raw))
    retry = retry_from_mapping(cast(dict[str, Any] | None, retry_raw))
    notify_raw = entry.get("notify_on_success", False)
    if not isinstance(notify_raw, bool):
        raise ValueError(
            f"jobs[{index}].notify_on_success deve ser booleano (true/false)"
        )
    # valida cedo para mensagens claras
    interval.to_apscheduler_kwargs()
    return JobConfig(
        id=job_id.strip(),
        name=name.strip(),
        interval=interval,
        retry=retry,
        notify_on_success=notify_raw,
    )


def load_scheduler_config(path: str | Path) -> SchedulerConfig:
    """Carrega e valida configuração YAML do agendador."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("Raiz do YAML deve ser um mapeamento (objeto)")
    jobs_raw = data.get("jobs")
    if jobs_raw is None:
        webhook = webhook_from_mapping(
            cast(dict[str, Any] | None, data.get("webhook"))
        )
        return SchedulerConfig(jobs=(), webhook=webhook)
    if not isinstance(jobs_raw, list):
        raise ValueError("'jobs' deve ser uma lista")
    jobs: list[JobConfig] = []
    for i, item in enumerate(jobs_raw):
        if not isinstance(item, dict):
            raise ValueError(f"jobs[{i}] deve ser um mapeamento")
        jobs.append(_parse_job(cast(dict[str, Any], item), i))
    webhook = webhook_from_mapping(
        cast(dict[str, Any] | None, data.get("webhook"))
    )
    return SchedulerConfig(jobs=tuple(jobs), webhook=webhook)


def webhook_from_mapping(data: dict[str, Any] | None) -> WebhookConfig:
    if data is None:
        return WebhookConfig()
    if not isinstance(data, dict):
        raise ValueError("'webhook' deve ser um mapeamento")
    raw_url = data.get("url")
    if raw_url is not None and not isinstance(raw_url, str):
        raise ValueError("webhook.url deve ser uma string ou omitido")
    url = raw_url.strip() if isinstance(raw_url, str) else None
    if url == "":
        url = None
    raw_timeout = data.get("timeout_seconds", 10.0)
    if not isinstance(raw_timeout, (int, float)):
        raise ValueError("webhook.timeout_seconds deve ser numérico")
    return WebhookConfig(url=url, timeout_seconds=float(raw_timeout))
