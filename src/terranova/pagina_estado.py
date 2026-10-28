"""Página pública de estado (`GET /estado`): la puerta y cada fuente según su último canario (F7.1).

Solo muestra lo que se mide: el último resultado de cada canario y su hora. No hay histórico de
disponibilidad, así que no hay porcentajes. HTML sin dependencias externas, legible en móvil.

Estado por fuente (a partir de sus herramientas):
- `verde`: todas pasaron en su último canario, verificado hace menos de `VIGENCIA`;
- `ambar`: unas pasan y otras no, o el último canario es más viejo que `VIGENCIA`;
- `rojo`: ninguna pasó;
- `sin_datos`: aún no tiene canario.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from html import escape

from terranova.catalogo import Catalogo
from terranova.vigilancia import Resultado

# los canarios corren a diario: con más de dos días sin resultado, la fuente no está verificada
VIGENCIA = timedelta(hours=48)
COLOMBIA = timezone(timedelta(hours=-5), "COT")  # sin horario de verano

ETIQUETA = {
    "rojo": "Con fallas",
    "ambar": "Degradada o sin verificar",
    "verde": "Operativa",
    "sin_datos": "Sin canario",
}
ORDEN = ["rojo", "ambar", "verde", "sin_datos"]


def _momento(texto: str) -> datetime:
    m = datetime.fromisoformat(texto)
    return m if m.tzinfo else m.replace(tzinfo=UTC)


def _hora(m: datetime) -> str:
    return m.astimezone(COLOMBIA).strftime("%Y-%m-%d %H:%M") + " (hora de Colombia)"


def estado_fuentes(
    ultimos: list[Resultado], catalogo: Catalogo, ahora: datetime
) -> list[dict[str, object]]:
    """Por fuente: estado, herramientas que pasan y total, y la hora del canario más reciente."""
    por_fuente: dict[str, list[Resultado]] = {}
    for r in ultimos:
        por_fuente.setdefault(r.fuente_id, []).append(r)
    salida: list[dict[str, object]] = []
    for fid, f in catalogo.fuentes.items():
        rs = por_fuente.get(fid, [])
        ultimo = max((_momento(r.momento) for r in rs), default=None)
        pasan = sum(r.ok for r in rs)
        if not rs or ultimo is None:
            estado = "sin_datos"
        elif pasan == 0:
            estado = "rojo"
        elif pasan < len(rs) or ahora - ultimo > VIGENCIA:
            estado = "ambar"
        else:
            estado = "verde"
        salida.append(
            {
                "fuente_id": fid,
                "titulo": f.titulo,
                "entidad": f.entidad,
                "estado": estado,
                "pasan": pasan,
                "total": len(rs),
                "ultimo": ultimo,
            }
        )
    salida.sort(key=lambda e: (ORDEN.index(str(e["estado"])), str(e["entidad"]), str(e["titulo"])))
    return salida


_ESTILO = """
:root{--fondo:#fafaf7;--texto:#1d1d1b;--suave:#5f5f5a;--borde:#e3e2dc;--tarjeta:#fff;
--verde:#1f7a3f;--ambar:#9a6400;--rojo:#b3261e;--gris:#76766f}
@media (prefers-color-scheme:dark){:root{--fondo:#151513;--texto:#ecebe6;--suave:#a9a8a1;
--borde:#2e2e2a;--tarjeta:#1d1d1a;--verde:#5cc283;--ambar:#e0a83c;--rojo:#f2867d;--gris:#9a9a92}}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--texto);
font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:1.5rem;margin:0 0 4px}h2{font-size:1.1rem;margin:32px 0 8px}
p{margin:4px 0}.suave{color:var(--suave);font-size:.9rem}
.puerta{border:1px solid var(--borde);background:var(--tarjeta);border-radius:8px;
padding:16px;margin:20px 0}
.resumen{display:flex;flex-wrap:wrap;gap:8px 20px;margin:12px 0}
.punto{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;
vertical-align:baseline}
.verde .punto{background:var(--verde)}.ambar .punto{background:var(--ambar)}
.rojo .punto{background:var(--rojo)}.sin_datos .punto{background:var(--gris)}
ul{list-style:none;margin:0;padding:0;border-top:1px solid var(--borde)}
li{display:flex;justify-content:space-between;gap:12px;padding:10px 0;
border-bottom:1px solid var(--borde)}
li .nombre{min-width:0;overflow-wrap:anywhere}li .lado{text-align:right;white-space:nowrap;
font-size:.9rem;color:var(--suave)}
@media (max-width:560px){li{flex-direction:column;gap:2px}li .lado{text-align:left}}
a{color:inherit}
"""


def pagina_estado(ultimos: list[Resultado], catalogo: Catalogo, ahora: datetime) -> str:
    fuentes = estado_fuentes(ultimos, catalogo, ahora)
    cuenta = {e: sum(f["estado"] == e for f in fuentes) for e in ORDEN}
    ultima = max((f["ultimo"] for f in fuentes if isinstance(f["ultimo"], datetime)), default=None)
    verificacion = _hora(ultima) if ultima else "todavía no hay canarios registrados"
    resumen = "".join(
        f'<span class="{e}"><span class="punto"></span>{ETIQUETA[e]}: {cuenta[e]}</span>'
        for e in ORDEN
    )
    filas = []
    for f in fuentes:
        estado = str(f["estado"])
        detalle = (
            f"{f['pasan']} de {f['total']} pruebas bien · {_hora(f['ultimo'])}"
            if isinstance(f["ultimo"], datetime)
            else "sin canario"
        )
        filas.append(
            f'<li class="{estado}"><span class="nombre"><span class="punto"></span>'
            f"<strong>{escape(str(f['titulo']))}</strong><br>"
            f'<span class="suave">{escape(str(f["entidad"]))} · {ETIQUETA[estado]}</span></span>'
            f'<span class="lado">{escape(detalle)}</span></li>'
        )
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Estado de Terranova</title>
<style>{_ESTILO}</style>
</head>
<body>
<main>
<h1>Estado de Terranova</h1>
<p class="suave">Generada el {_hora(ahora)}. Datos en JSON:
<a href="/v1/estado">/v1/estado</a>.</p>

<section class="puerta verde">
<p><span class="punto"></span><strong>La puerta responde</strong></p>
<p class="suave">Esta página la sirve la misma puerta que atiende la API y el MCP: si la ve, la
puerta está en línea.</p>
</section>

<h2>Fuentes oficiales</h2>
<p class="suave">Cada fuente se prueba a diario con un canario: una consulta con una respuesta
conocida, medida en la fuente. Última verificación: {verificacion}.</p>
<p class="suave">Las fuentes son de terceros (entidades públicas). Si una falla, la puerta responde
«no se pudo» y no inventa el dato.</p>
<div class="resumen">{resumen}</div>
<ul>
{chr(10).join(filas)}
</ul>
</main>
</body>
</html>
"""
