"""Métricas operativas en Prometheus (F7.2, spec 05 §12.2), en `/metrics` de cada réplica.

`/metrics` no sale a internet: Caddy lo bloquea en el borde y Prometheus lo lee por la red interna.
Las etiquetas son de un conjunto cerrado (herramientas y fuentes del catálogo, códigos de `rt/1`,
niveles): nada que venga de quien llama, para que no crezcan sin límite.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable

from prometheus_client import CollectorRegistry, Histogram, disable_created_metrics
from prometheus_client import Counter as Contador
from prometheus_client.core import GaugeMetricFamily, Metric
from prometheus_client.registry import Collector

disable_created_metrics()  # type: ignore[no-untyped-call]  # *_created solo hace ruido
REGISTRO = CollectorRegistry(auto_describe=True)
# del orden de un acierto de caché (ms) a la consulta más lenta de un conector (60 s)
CUBETAS = (0.05, 0.1, 0.3, 0.5, 1, 2, 5, 10, 15, 20, 30, 60)

SOLICITUDES = Contador(
    "rt_solicitudes",
    "Solicitudes por herramienta, estado del sobre (o «error») y código de error",
    ["herramienta", "estado", "codigo"],
    registry=REGISTRO,
)
LATENCIA = Histogram(
    "rt_latencia_segundos",
    "Latencia de la respuesta por herramienta y de dónde se sirvió",
    ["herramienta", "servido_desde"],
    buckets=CUBETAS,
    registry=REGISTRO,
)
FUENTE_LATENCIA = Histogram(
    "rt_fuente_latencia_segundos",
    "Latencia de cada llamada al conector de una fuente",
    ["fuente"],
    buckets=CUBETAS,
    registry=REGISTRO,
)
CACHE_ACIERTOS = Contador(
    "rt_cache_aciertos",
    "Respuestas servidas desde la caché sin consultar la fuente",
    registry=REGISTRO,
)
CREDITOS = Contador(
    "rt_creditos",
    "Créditos descontados, por nivel de la organización",
    ["nivel"],
    registry=REGISTRO,
)


class _AlRaspar(Collector):
    """Lo que se mide al momento de leer: circuitos, último canario y outbox pendiente."""

    def __init__(self) -> None:
        self.circuitos: Callable[[], Iterable[tuple[str, bool]]] = lambda: []
        self.canarios: Callable[[], Iterable[tuple[str, bool]]] = lambda: []
        self.outbox: Callable[[], int | None] = lambda: None

    def collect(self) -> Iterable[Metric]:
        circuito = GaugeMetricFamily(
            "rt_circuito_abierto",
            "1 si el cortacircuitos de la fuente está abierto",
            labels=["fuente"],
        )
        for fuente, abierto in self.circuitos():
            circuito.add_metric([fuente], 1.0 if abierto else 0.0)
        yield circuito
        canario = GaugeMetricFamily(
            "rt_canario",
            "Herramientas por fuente según su último canario (verde o rojo)",
            labels=["fuente", "resultado"],
        )
        cuenta = Counter((f, "verde" if ok else "rojo") for f, ok in self.canarios())
        for (fuente, resultado), n in sorted(cuenta.items()):
            canario.add_metric([fuente, resultado], float(n))
        yield canario
        pendientes = self.outbox()
        if pendientes is not None:
            yield GaugeMetricFamily(
                "rt_outbox_pendientes", "Eventos de uso aún no enviados", value=float(pendientes)
            )


AL_RASPAR = _AlRaspar()
REGISTRO.register(AL_RASPAR)
