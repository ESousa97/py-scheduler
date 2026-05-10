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
        raise ValueError(f"jobs[{index}].notify_on_success deve ser booleano (true/false)")
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
        webhook = webhook_from_mapping(cast(dict[str, Any] | None, data.get("webhook")))
        database_path = _parse_database_path(data.get("database_path"))
        jobs_register_module = _parse_optional_str(data.get("jobs_register_module"))
        metrics_enabled = _parse_metrics_enabled(data.get("metrics_enabled"))
        metrics_host = _parse_metrics_host(data.get("metrics_host"))
        metrics_port = _parse_metrics_port(data.get("metrics_port"))
        return SchedulerConfig(
            jobs=(),
            webhook=webhook,
            database_path=database_path,
            jobs_register_module=jobs_register_module,
            metrics_enabled=metrics_enabled,
            metrics_host=metrics_host,
            metrics_port=metrics_port,
        )
    if not isinstance(jobs_raw, list):
        raise ValueError("'jobs' deve ser uma lista")
    jobs: list[JobConfig] = []
    for i, item in enumerate(jobs_raw):
        if not isinstance(item, dict):
            raise ValueError(f"jobs[{i}] deve ser um mapeamento")
        jobs.append(_parse_job(cast(dict[str, Any], item), i))
    webhook = webhook_from_mapping(cast(dict[str, Any] | None, data.get("webhook")))
    database_path = _parse_database_path(data.get("database_path"))
    jobs_register_module = _parse_optional_str(data.get("jobs_register_module"))
    metrics_enabled = _parse_metrics_enabled(data.get("metrics_enabled"))
    metrics_host = _parse_metrics_host(data.get("metrics_host"))
    metrics_port = _parse_metrics_port(data.get("metrics_port"))
    return SchedulerConfig(
        jobs=tuple(jobs),
        webhook=webhook,
        database_path=database_path,
        jobs_register_module=jobs_register_module,
        metrics_enabled=metrics_enabled,
        metrics_host=metrics_host,
        metrics_port=metrics_port,
    )


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
    raw_silence = data.get("failure_alert_silence_minutes", 0.0)
    if raw_silence is None:
        silence_minutes = 0.0
    elif not isinstance(raw_silence, (int, float)):
        raise ValueError("webhook.failure_alert_silence_minutes deve ser numérico ou omitido")
    else:
        silence_minutes = float(raw_silence)
    return WebhookConfig(
        url=url,
        timeout_seconds=float(raw_timeout),
        failure_alert_silence_minutes=silence_minutes,
    )


def _parse_database_path(raw: Any) -> str:
    if raw is None:
        return "scheduler.sqlite"
    if not isinstance(raw, str):
        raise ValueError("database_path deve ser uma string ou omitido")
    return raw.strip()


def _parse_optional_str(raw: Any) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError("jobs_register_module deve ser uma string ou omitido")
    s = raw.strip()
    return s or None


def _parse_metrics_enabled(raw: Any) -> bool:
    if raw is None:
        return True
    if not isinstance(raw, bool):
        raise ValueError("metrics_enabled deve ser booleano (true/false)")
    return raw


def _parse_metrics_host(raw: Any) -> str:
    if raw is None:
        return "0.0.0.0"
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("metrics_host deve ser uma string não vazia")
    return raw.strip()


def _parse_metrics_port(raw: Any) -> int:
    if raw is None:
        return 9100
    if not isinstance(raw, int):
        raise ValueError("metrics_port deve ser um inteiro ou omitido")
    if raw < 1 or raw > 65535:
        raise ValueError("metrics_port deve estar entre 1 e 65535")
    return raw
