from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

from py_scheduler.app import _with_retry
from py_scheduler.loader import load_scheduler_config, webhook_from_mapping
from py_scheduler.models import (
    IntervalConfig,
    JobConfig,
    RetryConfig,
    WebhookConfig,
)
from py_scheduler.webhooks import WebhookNotifier


class _WebhookCaptureHandler(BaseHTTPRequestHandler):
    received: ClassVar[list[dict[str, Any]]] = []

    def log_message(self, format: str, *args: object) -> None:
        pass

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            _WebhookCaptureHandler.received.append(json.loads(raw.decode("utf-8")))
        except json.JSONDecodeError:
            _WebhookCaptureHandler.received.append({"_raw": raw.decode("utf-8", errors="replace")})
        self.send_response(204)
        self.end_headers()


class _RecorderNotifier:
    """Substituto mínimo de WebhookNotifier para testes de _with_retry."""

    def __init__(self) -> None:
        self.failed: list[tuple[str, str | None]] = []
        self.succeeded: list[str] = []

    @property
    def enabled(self) -> bool:
        return True

    def notify_job_failed(self, job_name: str, error: str | None) -> None:
        self.failed.append((job_name, error))

    def notify_job_succeeded(self, job_name: str) -> None:
        self.succeeded.append(job_name)


class TestLoaderWebhook(unittest.TestCase):
    def test_webhook_from_yaml(self) -> None:
        yaml = """
webhook:
  url: "https://example.com/hook"
  timeout_seconds: 5
jobs: []
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml)
            path = Path(f.name)
        try:
            cfg = load_scheduler_config(path)
            self.assertEqual(cfg.webhook.url, "https://example.com/hook")
            self.assertEqual(cfg.webhook.timeout_seconds, 5.0)
            self.assertEqual(len(cfg.jobs), 0)
        finally:
            path.unlink(missing_ok=True)

    def test_job_notify_on_success(self) -> None:
        yaml = """
webhook:
  url: https://example.com/h
jobs:
  - id: j1
    name: myjob
    interval: { seconds: 1 }
    notify_on_success: true
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml)
            path = Path(f.name)
        try:
            cfg = load_scheduler_config(path)
            self.assertTrue(cfg.jobs[0].notify_on_success)
        finally:
            path.unlink(missing_ok=True)

    def test_webhook_from_mapping_empty_url(self) -> None:
        w = webhook_from_mapping({"url": "   "})
        self.assertIsNone(w.url)


class TestWebhookNotifierHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _WebhookCaptureHandler.received.clear()
        cls._server = ThreadingHTTPServer(("127.0.0.1", 0), _WebhookCaptureHandler)
        cls._port = cls._server.server_address[1]
        cls._thread = threading.Thread(target=cls._server.serve_forever, daemon=True)
        cls._thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._server.shutdown()
        cls._server.server_close()
        cls._thread.join(timeout=5)

    def setUp(self) -> None:
        _WebhookCaptureHandler.received.clear()

    def test_post_failure_and_success_payloads(self) -> None:
        base = f"http://127.0.0.1:{self._port}/wh"
        cfg = WebhookConfig(url=base, timeout_seconds=5)
        n = WebhookNotifier.from_config(cfg)

        n.notify_job_failed("tarefa_x", "algo correu mal")
        n.notify_job_succeeded("tarefa_x")

        self.assertEqual(len(_WebhookCaptureHandler.received), 2)
        fail = _WebhookCaptureHandler.received[0]
        self.assertEqual(fail["event"], "job_failed")
        self.assertEqual(fail["job_name"], "tarefa_x")
        self.assertEqual(fail["error"], "algo correu mal")
        self.assertIn("timestamp", fail)
        self.assertIsInstance(fail["timestamp"], str)
        self.assertGreater(len(fail["timestamp"]), 10)

        ok = _WebhookCaptureHandler.received[1]
        self.assertEqual(ok["event"], "job_succeeded")
        self.assertEqual(ok["job_name"], "tarefa_x")
        self.assertNotIn("error", ok)
        self.assertIn("timestamp", ok)


class TestWithRetryWebhook(unittest.TestCase):
    def test_permanent_failure_triggers_webhook_once(self) -> None:
        job = JobConfig(
            id="id1",
            name="always_fail",
            interval=IntervalConfig(seconds=1),
            retry=RetryConfig(
                attempts=2,
                wait_multiplier_seconds=0.01,
                wait_min_seconds=0.0,
                wait_max_seconds=0.01,
            ),
        )
        rec = _RecorderNotifier()
        wrapped = _with_retry(
            job,
            lambda: (_ for _ in ()).throw(RuntimeError("falhou")),
            webhook_notifier=rec,  # type: ignore[arg-type]
        )
        with self.assertRaises(RuntimeError):
            wrapped()
        self.assertEqual(len(rec.failed), 1)
        self.assertEqual(rec.failed[0][0], "always_fail")
        self.assertIn("falhou", rec.failed[0][1] or "")
        self.assertEqual(rec.succeeded, [])

    def test_success_with_notify_on_success(self) -> None:
        job = JobConfig(
            id="id2",
            name="ok_job",
            interval=IntervalConfig(seconds=1),
            retry=RetryConfig(attempts=1),
            notify_on_success=True,
        )
        rec = _RecorderNotifier()
        wrapped = _with_retry(job, lambda: 42, webhook_notifier=rec)  # type: ignore[arg-type]
        self.assertEqual(wrapped(), 42)
        self.assertEqual(rec.succeeded, ["ok_job"])
        self.assertEqual(rec.failed, [])

    def test_success_without_notify(self) -> None:
        job = JobConfig(
            id="id3",
            name="silent",
            interval=IntervalConfig(seconds=1),
            retry=RetryConfig(attempts=1),
            notify_on_success=False,
        )
        rec = _RecorderNotifier()
        wrapped = _with_retry(job, lambda: None, webhook_notifier=rec)  # type: ignore[arg-type]
        wrapped()
        self.assertEqual(rec.succeeded, [])


if __name__ == "__main__":
    unittest.main()
