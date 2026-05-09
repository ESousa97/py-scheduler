from __future__ import annotations

import logging
import sys
from pathlib import Path

from py_scheduler import JobRegistry, SchedulerApp
from py_scheduler.example_jobs import (
    exemplo_manutencao,
    exemplo_relatorio,
    exemplo_tick,
)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Reduz ruído do APScheduler em INFO se desejado:
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


def _default_config_path() -> Path:
    return Path(__file__).resolve().parent / "config.example.yaml"


def main(argv: list[str] | None = None) -> int:
    _configure_logging()
    log = logging.getLogger("main")

    args = argv if argv is not None else sys.argv[1:]
    config_path = Path(args[0]) if args else _default_config_path()

    if not config_path.is_file():
        log.error("Arquivo de configuracao nao encontrado: %s", config_path)
        return 1

    registry = JobRegistry()
    registry.register("exemplo_tick", exemplo_tick)
    registry.register("exemplo_relatorio", exemplo_relatorio)
    registry.register("exemplo_manutencao", exemplo_manutencao)

    app = SchedulerApp(registry, config_path)

    try:
        app.run_forever()
    except KeyboardInterrupt:
        # Camada extra: caso algum codigo re-lance fora de run_forever
        log.info("Encerrado pelo usuario (KeyboardInterrupt).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
