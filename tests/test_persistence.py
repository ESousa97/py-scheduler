from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from py_scheduler.persistence import JobExecutionStore


class TestJobExecutionStore(unittest.TestCase):
    def test_roundtrip_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "db.sqlite"
            store = JobExecutionStore(str(path))
            store.record_execution(
                job_id="j1",
                job_name="n1",
                finished_at_iso="2026-01-01T00:00:00+00:00",
                duration_ms=12,
                outcome="success",
                attempt_number=1,
                error_type=None,
                error_message=None,
            )
            store.record_execution(
                job_id="j1",
                job_name="n1",
                finished_at_iso="2026-01-01T00:00:01+00:00",
                duration_ms=99,
                outcome="failed_final",
                attempt_number=2,
                error_type="RuntimeError",
                error_message="x",
            )
            conn = sqlite3.connect(str(path))
            try:
                cur = conn.execute(
                    "SELECT COUNT(*) FROM job_executions WHERE job_id = ?;", ("j1",)
                )
                self.assertEqual(cur.fetchone()[0], 2)
            finally:
                conn.close()

    def test_failure_webhook_muzzle_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "db.sqlite"
            store = JobExecutionStore(str(path))
            t0 = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
            self.assertIsNone(store.get_last_failure_webhook_alert_at("j1"))
            store.set_last_failure_webhook_alert_at("j1", t0)
            got = store.get_last_failure_webhook_alert_at("j1")
            assert got is not None
            self.assertEqual(got, t0)
            store.set_last_failure_webhook_alert_at(
                "j1", t0 + timedelta(minutes=5)
            )
            got2 = store.get_last_failure_webhook_alert_at("j1")
            assert got2 is not None
            self.assertEqual(got2, t0 + timedelta(minutes=5))
            store.clear_failure_webhook_muzzle("j1")
            self.assertIsNone(store.get_last_failure_webhook_alert_at("j1"))
