from __future__ import annotations

from collections.abc import Callable


class JobRegistry:
    """Mapeia nomes (str) para callables executados pelo agendador."""

    __slots__ = ("_jobs",)

    def __init__(self) -> None:
        self._jobs: dict[str, Callable[..., object]] = {}

    def register(self, name: str, func: Callable[..., object]) -> None:
        if name in self._jobs:
            raise ValueError(f"Job já registrado: {name!r}")
        self._jobs[name] = func

    def get(self, name: str) -> Callable[..., object]:
        try:
            return self._jobs[name]
        except KeyError as exc:
            raise KeyError(f"Nenhum job registrado com o nome: {name!r}") from exc

    def names(self) -> frozenset[str]:
        return frozenset(self._jobs)
