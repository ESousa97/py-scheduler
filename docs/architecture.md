# Architecture

**py-scheduler** is a thin orchestration layer around **APScheduler** with a YAML configuration file and a small Python extension point for registering callables.

## High-level flow

1. **CLI** (`py_scheduler/cli.py`) resolves the config path, configures **structlog**, loads YAML via **`load_scheduler_config`**, imports the jobs module, and calls **`register(registry)`**.
2. **`SchedulerApp`** (`py_scheduler/app.py`) reads the same YAML, optionally starts the **Prometheus** HTTP server, optionally opens **SQLite** for execution history, builds a **`BlockingScheduler`**, and registers one APScheduler job per YAML entry.
3. Each YAML job wraps the user callable with **Tenacity** retries (`_with_retry`). On failure paths it records rows (if persistence is enabled), updates metrics, logs, and may call the **webhook** client after the **final** failed attempt.
4. **Webhooks** (`py_scheduler/webhooks.py`) POST JSON payloads. When `failure_alert_silence_minutes` is set and SQLite is enabled, a per-job muzzle timestamp is stored to avoid spamming channels on repeated failures across restarts.

## Persistence schema (SQLite)

When `database_path` is non-empty, `JobExecutionStore` maintains a **`job_executions`** table with timestamps, duration, attempt number, outcome (`success`, `failed_retry`, `failed_final`), and optional error fields. Setting `database_path` to `""` disables all SQLite access from the app runtime path shown in `run_forever`.

## Metrics

`py_scheduler/metrics.py` starts `prometheus_client`’s WSGI server when enabled. Histograms and counters are labelled by `job_id` and `job_name` for Prometheus scrape compatibility.

## Extension point

User code should expose **`register(registry: JobRegistry) -> None`** and register stable string keys that match YAML `name` fields. See [ADDING_JOBS.md](ADDING_JOBS.md).
