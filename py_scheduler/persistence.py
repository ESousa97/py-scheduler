from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Literal

ExecutionOutcome = Literal["success", "failed_retry", "failed_final"]


class JobExecutionStore:
    """Persistência thread-safe de cada tentativa de execução (SQLite)."""

    __slots__ = ("_path", "_lock")

    def __init__(self, database_path: str) -> None:
        if not database_path:
            raise ValueError("database_path não pode ser vazio")
        self._path = Path(database_path)
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self._path,
            timeout=30.0,
            isolation_level=None,
            check_same_thread=False,
        )
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_schema(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS job_executions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL,
                        job_name TEXT NOT NULL,
                        finished_at TEXT NOT NULL,
                        duration_ms INTEGER NOT NULL,
                        outcome TEXT NOT NULL,
                        attempt_number INTEGER NOT NULL,
                        error_type TEXT,
                        error_message TEXT
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_job_executions_job_id
                    ON job_executions (job_id);
                    """
                )
            finally:
                conn.close()

    def record_execution(
        self,
        *,
        job_id: str,
        job_name: str,
        finished_at_iso: str,
        duration_ms: int,
        outcome: ExecutionOutcome,
        attempt_number: int,
        error_type: str | None,
        error_message: str | None,
    ) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO job_executions (
                        job_id, job_name, finished_at, duration_ms,
                        outcome, attempt_number, error_type, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        job_id,
                        job_name,
                        finished_at_iso,
                        duration_ms,
                        outcome,
                        attempt_number,
                        error_type,
                        error_message,
                    ),
                )
            finally:
                conn.close()
