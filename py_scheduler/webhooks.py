from __future__ import annotations

import http.client
import json
import ssl
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import structlog

from py_scheduler.models import WebhookConfig, webhook_url_has_allowed_scheme
from py_scheduler.persistence import JobExecutionStore

structured_logger = structlog.get_logger(__name__)


def _utc_iso_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _post_http_https(
    url: str,
    body: bytes,
    headers: dict[str, str],
    timeout: float,
) -> int:
    """POST só para http/https via http.client (sem urlopen / esquemas arbitrários)."""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError("apenas http e https são suportados")
    host = parsed.hostname
    if host is None:
        raise ValueError("URL sem hostname")
    port = parsed.port
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    if scheme == "https":
        conn: http.client.HTTPConnection = http.client.HTTPSConnection(
            host,
            port if port is not None else 443,
            timeout=timeout,
            context=ssl.create_default_context(),
        )
    else:
        conn = http.client.HTTPConnection(
            host,
            port if port is not None else 80,
            timeout=timeout,
        )
    try:
        conn.request("POST", path, body=body, headers=headers)
        resp = conn.getresponse()
        code = resp.status
        resp.read()
        return code
    finally:
        conn.close()


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
        url = url.strip()
        if not webhook_url_has_allowed_scheme(url):
            structured_logger.warning(
                "webhook_delivery_skipped",
                reason="disallowed_url_scheme",
                job_name=payload.get("job_name"),
                webhook_event=payload.get("event"),
            )
            return
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        hdrs = {"Content-Type": "application/json; charset=utf-8"}
        try:
            code = _post_http_https(url, body, hdrs, self._config.timeout_seconds)
            if code >= 400:
                structured_logger.warning(
                    "webhook_delivery_failed",
                    reason="http_error",
                    status=code,
                    job_name=payload.get("job_name"),
                    webhook_event=payload.get("event"),
                    error=f"HTTP {code}",
                )
            else:
                structured_logger.debug(
                    "webhook_sent",
                    status_code=code,
                    webhook_event=payload.get("event"),
                    job_name=payload.get("job_name"),
                )
        except ValueError as exc:
            structured_logger.warning(
                "webhook_delivery_failed",
                reason="bad_url",
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
