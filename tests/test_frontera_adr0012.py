"""ADR-0012 (la puerta no usa LLM) y ADR-0028 (los embeddings viven solo en el descubrimiento): la
frontera no puede quedar solo en la prosa. Aquí se comprueba, en un intérprete limpio, que importar
la ruta del dato (el ejecutor, los conectores, la puerta) no arrastra el modelo de embeddings ni su
orquestación. El buscador del catálogo embebe la consulta, pero por un conector interno que se carga
aparte, nunca al importar la puerta."""

import subprocess
import sys

# Módulos que NO deben aparecer al importar la ruta del dato: el modelo (fastembed/onnxruntime) y
# los que lo orquestan (descubrimiento, almacén). `terranova.descubrimiento` existe siempre (está en
# el paquete), así que la comprobación vale aunque el extra `descubrimiento` no esté instalado.
_PROHIBIDOS = (
    "fastembed",
    "onnxruntime",
    "terranova.descubrimiento",
    "terranova.almacen_descubrimiento",
)


def _importados_tras(importacion: str) -> str:
    codigo = (
        f"import sys; {importacion}; "
        f"print(','.join(m for m in {_PROHIBIDOS!r} if m in sys.modules))"
    )
    r = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, check=True)
    return r.stdout.strip()


def test_la_ruta_del_dato_no_importa_el_modelo_de_embeddings() -> None:
    assert _importados_tras("import terranova.ejecutor, terranova.conector") == ""


def test_importar_la_puerta_no_importa_el_modelo_de_embeddings() -> None:
    assert _importados_tras("import terranova.puerta") == ""
