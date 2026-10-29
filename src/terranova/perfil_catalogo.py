"""El perfil «catálogo» de la puerta (`/mcp/catalogo`): pocas herramientas genéricas en vez de una
por ficha, para los clientes que no buscan herramientas por su cuenta o que tienen tope (Windsurf
100, VS Code 128). Es el patrón de los proveedores de estadística (Data Commons, World Bank,
Census): buscar → consultar, con resolvedores de códigos al lado.

El buscador es híbrido: BM25 sobre el texto de cada herramienta (sale del catálogo) y, si hay
embebedor, el coseno con e5; los dos rankings se funden por rango recíproco (RRF). BM25 solo puede
quedar por debajo de no buscar (HumanMCP, 2026), por eso el denso suma cuando está. Los vectores se
calculan una vez por proceso, en segundo plano; mientras no estén, busca solo por palabras y lo
dice (`modo`).
"""

from __future__ import annotations

import logging
import math
import re
import threading
import unicodedata
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from terranova import ficha as ficha_lugar
from terranova.catalogo import Catalogo

if TYPE_CHECKING:
    from terranova.descubrimiento import Embedder

logger = logging.getLogger("terranova.perfil_catalogo")

#: Cuántas herramientas devuelve una búsqueda (Anthropic y OpenAI devuelven de 3 a 5; aquí un poco
#: más porque la entrada viene en el mismo resultado y no hace falta otra vuelta para describirla).
K_POR_DEFECTO = 6
_RRF = 60  # constante clásica de la fusión por rango recíproco
_PALABRAS_VACIAS = frozenset(
    "a al como con cual cuales cuanto cuantos cuantas de del donde el en es esta este hay la las "
    "lo los mas me mi o para por que se sobre su sus un una uno y ya cual cuál qué".split()
)


def _normalizar(texto: str) -> list[str]:
    """Minúsculas, sin tildes, partido en palabras y recortado a 6 letras: «contratos» y
    «contratación» caen en «contra», «municipio» y «municipal» en «munici». Burdo pero estable."""
    plano = unicodedata.normalize("NFKD", texto.lower())
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    palabras = re.findall(r"[a-z0-9]+", plano.replace("_", " "))
    return [p[:6] for p in palabras if p not in _PALABRAS_VACIAS and len(p) > 1]


@dataclass(frozen=True)
class Documento:
    herramienta: str
    familia: str
    texto: str


def documentos(catalogo: Catalogo) -> list[Documento]:
    """El texto que representa cada herramienta para buscarla: id, pregunta, descripción, fuente y
    entidad. Puro: mismo catálogo, mismos documentos."""
    docs = []
    for h in catalogo.herramientas.values():
        f = catalogo.fuentes.get(h.fuente)
        partes = [h.id.replace("_", " "), h.pregunta, h.descripcion]
        if f is not None:
            partes += [f.titulo, f.entidad]
        docs.append(Documento(h.id, h.familia, " · ".join(" ".join(p.split()) for p in partes)))
    docs.append(
        Documento(
            ficha_lugar.HERRAMIENTA,
            ficha_lugar.FAMILIA,
            f"ficha lugar · {ficha_lugar.PREGUNTA} · {ficha_lugar.DESCRIPCION}",
        )
    )
    return docs


class Bm25:
    """BM25 (k1=1.5, b=0.75) sobre los documentos ya normalizados."""

    def __init__(self, textos: Sequence[str]) -> None:
        self._docs = [Counter(_normalizar(t)) for t in textos]
        self._largos = [sum(d.values()) for d in self._docs]
        self._media = sum(self._largos) / max(len(self._docs), 1)
        df: Counter[str] = Counter()
        for d in self._docs:
            df.update(d.keys())
        n = len(self._docs)
        self._idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def puntajes(self, consulta: str) -> list[float]:
        terminos = _normalizar(consulta)
        salida = []
        for d, largo in zip(self._docs, self._largos, strict=True):
            s = 0.0
            for t in terminos:
                tf = d.get(t, 0)
                if tf:
                    s += self._idf[t] * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * largo / self._media))
            salida.append(s)
        return salida


def _coseno(a: Sequence[float], b: Sequence[float]) -> float:
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return sum(x * y for x, y in zip(a, b, strict=True)) / (na * nb)


def _rangos(puntajes: Sequence[float], minimo: float) -> dict[int, int]:
    """Posición (desde 0) de cada documento con puntaje > minimo, de mayor a menor."""
    orden = sorted((i for i, s in enumerate(puntajes) if s > minimo), key=lambda i: -puntajes[i])
    return {i: r for r, i in enumerate(orden)}


class IndiceHerramientas:
    """El índice del buscador. Construirlo es barato (BM25); los vectores se piden aparte
    (`vectorizar`) porque e5-large en CPU tarda ~1 min para todo el catálogo."""

    def __init__(self, docs: list[Documento], embedder: Embedder | None = None) -> None:
        self.docs = docs
        self._bm25 = Bm25([d.texto for d in docs])
        self._embedder = embedder
        self._vectores: list[tuple[float, ...]] | None = None
        self._candado = threading.Lock()

    @property
    def modo(self) -> str:
        return "hibrido" if self._vectores is not None else "palabras"

    def vectorizar(self) -> None:
        """Embebe los documentos (bloqueante; corre en un hilo). Si falla, el índice sigue por
        palabras: buscar nunca se cae por el embebedor."""
        if self._embedder is None or self._vectores is not None:
            return
        with self._candado:
            if self._vectores is not None:
                return
            try:
                vectores: list[tuple[float, ...]] = []
                for i in range(0, len(self.docs), 8):  # e5-large en CPU: lotes chicos
                    lote = [d.texto[:1000] for d in self.docs[i : i + 8]]
                    vectores += self._embedder.documentos(lote)
                self._vectores = vectores
            except Exception:
                logger.warning("no se pudo vectorizar el catálogo de herramientas", exc_info=True)

    def vectorizar_en_segundo_plano(self) -> None:
        if self._embedder is not None and self._vectores is None:
            threading.Thread(target=self.vectorizar, daemon=True, name="indice-herr").start()

    def buscar(
        self, consulta: str, familia: str | None = None, k: int = K_POR_DEFECTO
    ) -> list[Documento]:
        rangos = [_rangos(self._bm25.puntajes(consulta), 0.0)]
        if self._vectores is not None and self._embedder is not None:
            try:
                q = self._embedder.consulta(consulta)
                rangos.append(_rangos([_coseno(q, v) for v in self._vectores], -1.0))
            except Exception:
                logger.warning("el embebedor falló; se busca por palabras", exc_info=True)
        puntaje: dict[int, float] = {}
        for r in rangos:
            for i, pos in r.items():
                puntaje[i] = puntaje.get(i, 0.0) + 1.0 / (_RRF + pos)
        orden = sorted(puntaje, key=lambda i: -puntaje[i])
        if familia:
            orden = [i for i in orden if self.docs[i].familia == familia]
        return [self.docs[i] for i in orden[:k]]


#: Qué cubre cada familia, para que el agente sepa qué existe antes de buscar (Speakeasy: con
#: búsqueda semántica sola, el modelo a veces no busca porque no sabe qué hay).
TEMAS_FAMILIA = {
    "territorio": "catastro y predios (IGAC, Bogotá), amenazas y riesgo, áreas protegidas, POT, "
    "minería, red vial, aeropuertos y puertos",
    "contratacion": "contratos públicos SECOP I y II, procesos, proveedores, planes de compras",
    "empresas": "RUES por NIT o nombre, Supersociedades, Superfinanciera, Supersolidaria",
    "normativa": "normas (SUIN, Función Pública, DIAN, CREG), sentencias de la Corte",
    "justicia": "delitos y lesiones (Policía), víctimas (RUV, CNMH), Medicina Legal, minas",
    "estadisticas": "población (DANE), IPC, PIB, empleo, pobreza (IPM), educación (ICFES), "
    "salud (REPS, ADRES), comercio exterior, hidrocarburos (ANH), tráfico aéreo y peajes",
    "ambiente": "clima y estaciones IDEAM, alertas, calidad del aire, bosques, incendios",
    "meta": "buscador de datasets abiertos del catálogo nacional",
}


def mapa_de_familias(catalogo: Catalogo) -> str:
    cuentas = Counter(h.familia for h in catalogo.herramientas.values())
    return "; ".join(
        f"{f} ({cuentas[f]}): {TEMAS_FAMILIA.get(f, '')}".rstrip(": ")
        for f in sorted(cuentas, key=lambda f: -cuentas[f])
    )


def indice_desde_entorno(
    catalogo: Catalogo, embedder_desde: Callable[[], Embedder | None]
) -> IndiceHerramientas:
    return IndiceHerramientas(documentos(catalogo), embedder_desde())
