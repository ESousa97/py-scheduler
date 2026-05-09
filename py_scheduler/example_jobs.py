from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


def exemplo_tick() -> None:
    logger.info("tick: %s", time.strftime("%H:%M:%S"))


def exemplo_relatorio() -> None:
    logger.info("relatorio simulado (intervalo em minutos)")


def exemplo_manutencao() -> None:
    logger.info("manutencao simulada (intervalo em horas)")
