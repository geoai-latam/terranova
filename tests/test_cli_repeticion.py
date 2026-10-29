"""Los jobs del compose (canarios, copias) corren a hora fija: un despliegue no mueve la hora."""

import argparse
from datetime import UTC, datetime

import pytest

from terranova import cli


def test_hora_utc() -> None:
    assert cli.hora_utc("09:00") == (9, 0)
    assert cli.hora_utc("23:59") == (23, 59)
    for mala in ("24:00", "9", "09:60", "nueve"):
        with pytest.raises(argparse.ArgumentTypeError):
            cli.hora_utc(mala)


def test_segundos_hasta_la_proxima() -> None:
    ahora = datetime(2026, 10, 29, 8, 30, tzinfo=UTC)
    assert cli.segundos_hasta((9, 0), ahora) == 30 * 60  # hoy
    assert cli.segundos_hasta((8, 0), ahora) == 23.5 * 3600  # ya pasó: mañana
    assert cli.segundos_hasta((8, 30), ahora) == 24 * 3600  # justo ahora: mañana


def test_a_las_espera_antes_de_correr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Al arrancar no corre: espera a la hora; luego corre y vuelve a esperar."""
    pasos: list[str] = []

    class Fin(Exception):
        pass

    def dormir(s: float) -> None:
        pasos.append("espera")
        if len(pasos) > 3:
            raise Fin

    def una_vez() -> bool:
        pasos.append("corre")
        return True

    monkeypatch.setattr("time.sleep", dormir)
    with pytest.raises(Fin):
        cli.repetir(una_vez, (9, 0), None)
    assert pasos == ["espera", "corre", "espera", "corre", "espera"]


def test_sin_repeticion_corre_una_vez() -> None:
    assert cli.repetir(lambda: True, None, None) == 0
    assert cli.repetir(lambda: False, None, None) == 1


def test_a_las_y_cada_horas_se_excluyen() -> None:
    parser = argparse.ArgumentParser()
    cli._opciones_de_repeticion(parser)
    with pytest.raises(SystemExit):
        parser.parse_args(["--a-las", "09:00", "--cada-horas", "24"])
    assert parser.parse_args(["--a-las", "09:00"]).a_las == (9, 0)
