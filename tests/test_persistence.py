from __future__ import annotations

import sqlite3
import tempfile
import unittest
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
