from __future__ import annotations

import logging
import time

from py_scheduler.registry import JobRegistry

logger = logging.getLogger(__name__)


def register(registry: JobRegistry) -> None:
    """Registra os jobs de exemplo; módulos próprios devem expor a mesma função."""
    registry.register("exemplo_tick", exemplo_tick)
    registry.register("exemplo_relatorio", exemplo_relatorio)
    registry.register("exemplo_manutencao", exemplo_manutencao)


def exemplo_tick() -> None:
    logger.info("tick: %s", time.strftime("%H:%M:%S"))


def exemplo_relatorio() -> None:
    logger.info("relatorio simulado (intervalo em minutos)")


def exemplo_manutencao() -> None:
    logger.info("manutencao simulada (intervalo em horas)")
