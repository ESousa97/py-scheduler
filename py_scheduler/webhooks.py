from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import structlog

from py_scheduler.models import WebhookConfig

structured_logger = structlog.get_logger(__name__)


def _utc_iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class WebhookNotifier:
    """POST HTTP com JSON; não faz nada se `url` estiver vazia ou ausente."""

    _config: WebhookConfig

    @classmethod
    def from_config(cls, config: WebhookConfig) -> WebhookNotifier:
        return cls(_config=config)

    @property
    def enabled(self) -> bool:
        u = self._config.url
        return u is not None and bool(u.strip())

    def notify_job_failed(self, job_name: str, error: str | None) -> None:
        if not self.enabled:
            return
        payload: dict[str, Any] = {
            "event": "job_failed",
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
            with urllib.request.urlopen(
                req, timeout=self._config.timeout_seconds
            ) as resp:
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
