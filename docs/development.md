# Development

## Prerequisites

- Python **3.11+**
- `git` and `pip`

## Install (editable, with dev tools)

```bash
pip install -e ".[dev]"
```

This installs **pytest**, **pytest-cov**, and **Ruff** alongside runtime dependencies declared in `pyproject.toml`.

## Lint and format

```bash
ruff check .
ruff format --check .
```

Auto-fix:

```bash
ruff check . --fix
ruff format .
```

## Tests

```bash
pytest -q
```

Coverage (mirrors CI on Python 3.12):

```bash
pytest --cov=py_scheduler --cov-report=term-missing
```

## Fast wiring check

Without starting the blocking scheduler:

```bash
python scripts/smoke_validate.py
# optional: path to another YAML file
python scripts/smoke_validate.py /path/to/config.yaml
```

## Run the scheduler locally

```bash
python main.py config.example.yaml
```

Press **Ctrl+C** to shut down gracefully (`shutdown(wait=True)`).

## Docker

Build and run (expose metrics on host port 9100):

```bash
docker build -t py-scheduler .
docker run --rm -p 9100:9100 py-scheduler
```

Mount custom config and persistent SQLite:

```bash
docker run --rm -p 9100:9100 \
  -v "$(pwd)/my-config.yaml:/app/config/config.yaml:ro" \
  -v py-scheduler-data:/data \
  -e PY_SCHEDULER_JOBS_MODULE=mycompany.scheduler_jobs \
  py-scheduler
```

Set `database_path: /data/scheduler.sqlite` in your YAML when using the `/data` volume.

## Adding jobs without forking core

See [ADDING_JOBS.md](ADDING_JOBS.md).

## pre-commit

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

Hooks are defined in [`.pre-commit-config.yaml`](../.pre-commit-config.yaml).
