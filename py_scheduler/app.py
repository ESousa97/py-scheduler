from __future__ import annotations

import logging
from pathlib import Path

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers import SchedulerNotRunningError
from apscheduler.schedulers.blocking import BlockingScheduler

from py_scheduler.loader import load_scheduler_config
from py_scheduler.models import SchedulerConfig
from py_scheduler.registry import JobRegistry

logger = logging.getLogger(__name__)


class SchedulerApp:
    """Monta APScheduler a partir de registry + arquivo YAML."""

    __slots__ = ("_registry", "_config_path")

    def __init__(self, registry: JobRegistry, config_path: str | Path) -> None:
        self._registry = registry
        self._config_path = Path(config_path)

    def load_config(self) -> SchedulerConfig:
        return load_scheduler_config(self._config_path)

    def build_scheduler(self, config: SchedulerConfig | None = None) -> BlockingScheduler:
        cfg = config if config is not None else self.load_config()
        executors = {"default": ThreadPoolExecutor(max_workers=4)}
        job_defaults: dict[str, object] = {"coalesce": True, "max_instances": 1}
        scheduler = BlockingScheduler(
            executors=executors,
            job_defaults=job_defaults,
        )
        for job in cfg.jobs:
            func = self._registry.get(job.name)
            kwargs = job.interval.to_apscheduler_kwargs()
            scheduler.add_job(
                func,
                trigger="interval",
                id=job.id,
                replace_existing=True,
                **kwargs,
            )
        return scheduler

    def run_forever(self) -> None:
        """Inicia o scheduler até interrupção; encerra com shutdown(wait=True)."""
        scheduler: BlockingScheduler | None = None
        try:
            scheduler = self.build_scheduler()
            n = len(scheduler.get_jobs())
            logger.info(
                "Iniciando py-scheduler com %d job(s); Ctrl+C para encerrar.",
                n,
            )
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt: encerrando graciosamente.")
        finally:
            if scheduler is not None:
                try:
                    scheduler.shutdown(wait=True)
                    logger.info("Scheduler parado.")
                except SchedulerNotRunningError:
                    logger.debug("Scheduler nunca chegou a rodar; shutdown ignorado.")
