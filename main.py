from __future__ import annotations

import importlib
import logging
import os
import sys
from pathlib import Path

import structlog

from py_scheduler import JobRegistry, SchedulerApp
from py_scheduler.loader import load_scheduler_config


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    # Reduz ruído do APScheduler em INFO se desejado:
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


def _default_config_path() -> Path:
    return Path(__file__).resolve().parent / "config.example.yaml"


def _jobs_register_module_from_env_and_config(config_module: str | None) -> str:
    return (
        config_module
        or os.environ.get("PY_SCHEDULER_JOBS_MODULE")
        or "py_scheduler.example_jobs"
    )


def _populate_registry(registry: JobRegistry, module_name: str) -> None:
    mod = importlib.import_module(module_name)
    register = getattr(mod, "register", None)
    if register is None:
        raise RuntimeError(
            f"O módulo {module_name!r} deve definir register(registry: JobRegistry) -> None"
        )
    register(registry)


def main(argv: list[str] | None = None) -> int:
    _configure_logging()
    log = structlog.get_logger("main")

    args = argv if argv is not None else sys.argv[1:]
    config_path = Path(args[0]) if args else _default_config_path()

    if not config_path.is_file():
        log.error("config_file_not_found", config_path=str(config_path))
        return 1

    cfg = load_scheduler_config(config_path)
    module_name = _jobs_register_module_from_env_and_config(cfg.jobs_register_module)
    registry = JobRegistry()
    try:
        _populate_registry(registry, module_name)
    except (
        ImportError,
        ModuleNotFoundError,
        RuntimeError,
        AttributeError,
        ValueError,
    ) as exc:
        log.error(
            "jobs_register_failed",
            module_name=module_name,
            error=str(exc),
        )
        return 1

    app = SchedulerApp(registry, config_path)

    try:
        app.run_forever()
    except KeyboardInterrupt:
        # Camada extra: caso algum codigo re-lance fora de run_forever
        log.info("shutdown_requested")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
