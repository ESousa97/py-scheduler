from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from py_scheduler.models import WebhookConfig
from py_scheduler.persistence import JobExecutionStore

structured_logger = structlog.get_logger(__name__)


def _utc_iso_timestamp() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class WebhookNotifier:
    """POST HTTP com JSON; não faz nada se `url` estiver vazia ou ausente."""

    _config: WebhookConfig
    # Se definido e `failure_alert_silence_minutes` > 0, o muzzle persiste no SQLite.
    _execution_store: JobExecutionStore | None = None
    _failure_alert_lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False
    )
    _last_failure_alert_at: dict[str, datetime] = field(
        default_factory=dict, init=False, repr=False
    )

    @classmethod
    def from_config(
        cls,
        config: WebhookConfig,
        *,
        execution_store: JobExecutionStore | None = None,
    ) -> WebhookNotifier:
        return cls(_config=config, _execution_store=execution_store)

    @property
    def enabled(self) -> bool:
        u = self._config.url
        return u is not None and bool(u.strip())

    def clear_failure_alert_silence(self, job_id: str) -> None:
        """Chamar após sucesso: o próximo `job_failed` volta a poder alertar de imediato."""
        with self._failure_alert_lock:
            self._last_failure_alert_at.pop(job_id, None)
            if self._execution_store is not None:
                self._execution_store.clear_failure_webhook_muzzle(job_id)

    def notify_job_failed(self, job_id: str, job_name: str, error: str | None) -> None:
        if not self.enabled:
            return
        silence_minutes = self._config.failure_alert_silence_minutes
        now = datetime.now(UTC)
        with self._failure_alert_lock:
            if silence_minutes > 0:
                last = (
                    self._execution_store.get_last_failure_webhook_alert_at(job_id)
                    if self._execution_store is not None
                    else self._last_failure_alert_at.get(job_id)
                )
                if last is not None:
                    elapsed_minutes = (now - last).total_seconds() / 60.0
                    if elapsed_minutes < silence_minutes:
                        structured_logger.info(
                            "failure_webhook_muzzled",
                            job_id=job_id,
                            job_name=job_name,
                            silence_minutes=silence_minutes,
                            minutes_since_last_alert=round(elapsed_minutes, 4),
                        )
                        return
                if self._execution_store is not None:
                    self._execution_store.set_last_failure_webhook_alert_at(job_id, now)
                else:
                    self._last_failure_alert_at[job_id] = now
        payload: dict[str, Any] = {
            "event": "job_failed",
            "job_id": job_id,
            "job_name": job_name,
            "error": error if error is not None else "",
            "timestamp": _utc_iso_timestamp(),
        }
        self._send(payload)

    def notify_job_succeeded(self, job_name: str) -> None:
        if not self.enabled:
            return
        payload: dict[str, Any] = {
            "event": "job_succeeded",
            "job_name": job_name,
            "timestamp": _utc_iso_timestamp(),
        }
        self._send(payload)

    def _send(self, payload: dict[str, Any]) -> None:
        url = self._config.url
        assert url is not None
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url.strip(),
            data=body,
            method="POST",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self._config.timeout_seconds) as resp:
                code = getattr(resp, "status", resp.getcode())
                structured_logger.debug(
                    "webhook_sent",
                    status_code=code,
                    webhook_event=payload.get("event"),
                    job_name=payload.get("job_name"),
                )
        except urllib.error.HTTPError as exc:
            structured_logger.warning(
                "webhook_delivery_failed",
                reason="http_error",
                status=exc.code,
                job_name=payload.get("job_name"),
                webhook_event=payload.get("event"),
                error=str(exc),
            )
        except urllib.error.URLError as exc:
            structured_logger.warning(
                "webhook_delivery_failed",
                reason="url_error",
                job_name=payload.get("job_name"),
                webhook_event=payload.get("event"),
                error=str(exc),
            )
        except TimeoutError as exc:
            structured_logger.warning(
                "webhook_delivery_failed",
                reason="timeout",
                job_name=payload.get("job_name"),
                webhook_event=payload.get("event"),
                error=str(exc),
            )
        except OSError as exc:
            structured_logger.warning(
                "webhook_delivery_failed",
                reason="os_error",
                job_name=payload.get("job_name"),
                webhook_event=payload.get("event"),
                error=str(exc),
            )
