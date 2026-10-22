"""Errores de la puerta: fallos totales con un código estable de `rt/1` (spec 01, §6.3)."""

from __future__ import annotations


class ErrorEntrada(Exception):
    """Entrada que no cumple su tipo: `parametro_invalido`, no se llama a la fuente."""

    def __init__(self, param: str, mensaje: str) -> None:
        super().__init__(f"{param}: {mensaje}")
        self.param = param


class ErrorEjecucion(Exception):
    """Fallo total: no hay sobre, hay un error con código estable."""

    def __init__(self, codigo: str, mensaje: str, reintentar_en_s: int | None = None) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.reintentar_en_s = reintentar_en_s
