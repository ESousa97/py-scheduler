from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from py_scheduler.models import (
    IntervalConfig,
    JobConfig,
    SchedulerConfig,
    interval_from_mapping,
)


def _parse_job(entry: dict[str, Any], index: int) -> JobConfig:
    job_id = entry.get("id")
    name = entry.get("name")
    interval_raw = entry.get("interval")
    if not isinstance(job_id, str) or not job_id.strip():
        raise ValueError(f"jobs[{index}].id deve ser uma string não vazia")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"jobs[{index}].name deve ser uma string não vazia")
    if not isinstance(interval_raw, dict):
        raise ValueError(f"jobs[{index}].interval deve ser um mapeamento")
    interval = interval_from_mapping(cast(dict[str, Any], interval_raw))
    # valida cedo para mensagens claras
    interval.to_apscheduler_kwargs()
    return JobConfig(id=job_id.strip(), name=name.strip(), interval=interval)


def load_scheduler_config(path: str | Path) -> SchedulerConfig:
    """Carrega e valida configuração YAML do agendador."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("Raiz do YAML deve ser um mapeamento (objeto)")
    jobs_raw = data.get("jobs")
    if jobs_raw is None:
        return SchedulerConfig(jobs=())
    if not isinstance(jobs_raw, list):
        raise ValueError("'jobs' deve ser uma lista")
    jobs: list[JobConfig] = []
    for i, item in enumerate(jobs_raw):
        if not isinstance(item, dict):
            raise ValueError(f"jobs[{i}] deve ser um mapeamento")
        jobs.append(_parse_job(cast(dict[str, Any], item), i))
    return SchedulerConfig(jobs=tuple(jobs))
