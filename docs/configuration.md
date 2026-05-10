# Configuration

Configuration is a **single YAML file** passed as the first CLI argument, or defaults to the bundled `config.example.yaml` when no argument is provided.

## Environment variables

| Variable | Purpose |
| -------- | ------- |
| `PY_SCHEDULER_JOBS_MODULE` | Dotted import path for the module that defines `register(registry)`. Ignored when `jobs_register_module` is set in YAML. |

## Top-level YAML keys

| Key | Type | Default | Description |
| --- | ---- | ------- | ----------- |
| `jobs` | list | _(required for a useful run)_ | Job definitions (see below). |
| `webhook` | object | omitted | Optional HTTP notifications (see below). |
| `database_path` | string | `scheduler.sqlite` | SQLite path for execution history and webhook muzzle state. Use `""` to disable persistence. |
| `jobs_register_module` | string | `null` | Overrides `PY_SCHEDULER_JOBS_MODULE` when set. |
| `metrics_enabled` | bool | `true` | When `false`, the `/metrics` HTTP server is not started. |
| `metrics_host` | string | `127.0.0.1` | Bind address for metrics. Use `0.0.0.0` only when you intend to expose `/metrics` on all interfaces (for example behind a firewall or in a container). |
| `metrics_port` | int | `9100` | TCP port for metrics. |

## `jobs[]` entries

| Key | Type | Required | Description |
| --- | ---- | -------- | ----------- |
| `id` | string | yes | Stable APScheduler job id (`replace_existing=True`). |
| `name` | string | yes | Registry key passed to `registry.register(...)`. |
| `interval` | object | yes | At least one of `seconds`, `minutes`, `hours` (integers). |
| `retry` | object | no | Tenacity policy: `attempts`, `wait_multiplier_seconds`, `wait_min_seconds`, `wait_max_seconds`. |
| `notify_on_success` | bool | `false` | When `true` and a webhook URL is configured, POST after each successful run. |

## `webhook` object

| Key | Type | Default | Description |
| --- | ---- | ------- | ----------- |
| `url` | string | `null` | HTTPS endpoint accepting JSON POST (Slack/Discord-compatible patterns). |
| `timeout_seconds` | number | `10` | HTTP client timeout. |
| `failure_alert_silence_minutes` | number | `0` | After a failure alert for a job id, suppress duplicate failure webhooks for N minutes (requires SQLite for cross-restart behaviour). |
