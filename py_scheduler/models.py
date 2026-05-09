from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class IntervalConfig:
    """Intervalo para trigger do tipo 'interval' do APScheduler."""

    seconds: int | None = None
    minutes: int | None = None
    hours: int | None = None

    def to_apscheduler_kwargs(self) -> dict[str, int]:
        """Converte para kwargs aceitos por add_job(..., 'interval', ...)."""
        kwargs: dict[str, int] = {}
        if self.seconds is not None:
            kwargs["seconds"] = self.seconds
        if self.minutes is not None:
            kwargs["minutes"] = self.minutes
        if self.hours is not None:
            kwargs["hours"] = self.hours
        if not kwargs:
            raise ValueError(
                "IntervalConfig precisa de pelo menos um entre: seconds, minutes, hours"
            )
        return kwargs


@dataclass(frozen=True, slots=True)
class JobConfig:
    """Especificação de um job carregada do YAML."""

    id: str
    name: str
    interval: IntervalConfig


@dataclass(frozen=True, slots=True)
class SchedulerConfig:
    """Configuração raiz do agendador."""

    jobs: tuple[JobConfig, ...]


def interval_from_mapping(data: dict[str, Any]) -> IntervalConfig:
    raw_seconds = data.get("seconds")
    raw_minutes = data.get("minutes")
    raw_hours = data.get("hours")
    seconds = int(raw_seconds) if raw_seconds is not None else None
    minutes = int(raw_minutes) if raw_minutes is not None else None
    hours = int(raw_hours) if raw_hours is not None else None
    return IntervalConfig(seconds=seconds, minutes=minutes, hours=hours)
