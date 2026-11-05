"""Un «no encontrado» sin explicación no sirve: quien pregunta no sabe si no hay datos, si escribió
mal el código o si el año no está. Toda herramienta dice por qué no encontró nada, con su aviso
`cuando: vacio` o con el `aviso_vacio` de su fuente. Las que aún no lo tienen están en
`sin_aviso_vacio.txt`, y esa lista solo puede bajar."""

from pathlib import Path

from terranova.catalogo import cargar

LISTA = Path(__file__).parent / "sin_aviso_vacio.txt"


def _pendientes() -> set[str]:
    lineas = LISTA.read_text(encoding="utf-8").splitlines()
    return {x.strip() for x in lineas if x.strip() and not x.startswith("#")}


def _sin_aviso() -> set[str]:
    c = cargar()
    return {
        i
        for i, h in c.herramientas.items()
        if not any(a.cuando == "vacio" for a in h.avisos or [])
        and not c.fuentes[h.fuente].cobertura.aviso_vacio
    }


def test_toda_herramienta_nueva_explica_su_vacio() -> None:
    nuevas = sorted(_sin_aviso() - _pendientes())
    assert not nuevas, (
        f"sin aviso de vacío: {nuevas}. Añada `- cuando: vacio` con el porqué (no hay datos, el "
        "código no existe, el año no está) a sus `avisos`."
    )


def test_la_lista_de_pendientes_no_tiene_herramientas_que_no_existen() -> None:
    ids = set(cargar().herramientas)
    assert not sorted(_pendientes() - ids)
