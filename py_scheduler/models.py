from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


def webhook_url_has_allowed_scheme(url: str) -> bool:
    """True apenas para http/https (evita file:, ftp:, etc. em urlopen)."""
    return urlparse(url.strip()).scheme.lower() in ("http", "https")


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
class RetryConfig:
    """Política de retry aplicada à execução de um job."""

    attempts: int = 3
    wait_multiplier_seconds: float = 1.0
    wait_min_seconds: float = 1.0
    wait_max_seconds: float = 60.0

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError("RetryConfig.attempts deve ser maior ou igual a 1")
        if self.wait_multiplier_seconds <= 0:
            raise ValueError("RetryConfig.wait_multiplier_seconds deve ser maior que zero")
        if self.wait_min_seconds < 0:
            raise ValueError("RetryConfig.wait_min_seconds deve ser maior ou igual a zero")
        if self.wait_max_seconds < self.wait_min_seconds:
            raise ValueError("RetryConfig.wait_max_seconds deve ser maior ou igual ao minimo")


@dataclass(frozen=True, slots=True)
class JobConfig:
    """Especificação de um job carregada do YAML."""

    id: str
    name: str
    interval: IntervalConfig
    retry: RetryConfig = RetryConfig()
    # Se True e webhook configurado, envia POST após sucesso (tarefas críticas).
    notify_on_success: bool = False


@dataclass(frozen=True, slots=True)
class WebhookConfig:
    """URL opcional para alertas (Slack, Discord, etc.) via POST JSON."""

    url: str | None = None
    timeout_seconds: float = 10.0
    # Muzzle: após enviar um alerta de falha para um job, não reenvia por N minutos
    # (evita spam no canal se a tarefa continua a falhar em ciclo). 0 = desligado.
    failure_alert_silence_minutes: float = 0.0

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("WebhookConfig.timeout_seconds deve ser maior que zero")
        if self.failure_alert_silence_minutes < 0:
            raise ValueError(
                "WebhookConfig.failure_alert_silence_minutes deve ser maior ou igual a zero"
            )
        if self.url is not None and not webhook_url_has_allowed_scheme(self.url):
            raise ValueError("WebhookConfig.url deve usar o esquema http ou https")


@dataclass(frozen=True, slots=True)
class SchedulerConfig:
    """Configuração raiz do agendador."""

    jobs: tuple[JobConfig, ...]
    webhook: WebhookConfig = WebhookConfig()
    # Caminho do SQLite para histórico de execuções (string vazia desativa persistência).
    database_path: str = "scheduler.sqlite"
    # Módulo Python com função register(registry) — ver docs/ADDING_JOBS.md.
    jobs_register_module: str | None = None
    # Servidor HTTP do prometheus_client (expondo /metrics).
    metrics_enabled: bool = True
    metrics_host: str = "127.0.0.1"
    metrics_port: int = 9100


def interval_from_mapping(data: dict[str, Any]) -> IntervalConfig:
    raw_seconds = data.get("seconds")
    raw_minutes = data.get("minutes")
    raw_hours = data.get("hours")
    seconds = int(raw_seconds) if raw_seconds is not None else None
    minutes = int(raw_minutes) if raw_minutes is not None else None
    hours = int(raw_hours) if raw_hours is not None else None
    return IntervalConfig(seconds=seconds, minutes=minutes, hours=hours)


def retry_from_mapping(data: dict[str, Any] | None) -> RetryConfig:
    if data is None:
        return RetryConfig()
    raw_attempts = data.get("attempts", RetryConfig.attempts)
    raw_multiplier = data.get(
        "wait_multiplier_seconds",
        RetryConfig.wait_multiplier_seconds,
    )
    raw_min = data.get("wait_min_seconds", RetryConfig.wait_min_seconds)
    raw_max = data.get("wait_max_seconds", RetryConfig.wait_max_seconds)
    return RetryConfig(
        attempts=int(raw_attempts),
        wait_multiplier_seconds=float(raw_multiplier),
        wait_min_seconds=float(raw_min),
        wait_max_seconds=float(raw_max),
    )
