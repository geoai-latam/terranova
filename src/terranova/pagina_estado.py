"""Página pública de estado (`GET /estado`): la puerta y cada fuente según su último canario (F7.1).

Solo muestra lo que se mide: el último resultado de cada canario y su hora. No hay histórico de
disponibilidad, así que no hay porcentajes. Sin scripts ni recursos de otros dominios: toma Geist
de `/estilo.css` del sitio cuando Caddy lo sirve y, sin él, sigue legible en móvil.

Estado por fuente (a partir de sus herramientas):
- `verde`: todas pasaron en su último canario, verificado hace menos de `VIGENCIA`;
- `ambar`: unas pasan y otras no, lo único que falla es lentitud o una copia vencida, o el último
  canario es más viejo que `VIGENCIA`;
- `rojo`: ninguna pasó y alguna falló de verdad (no solo lenta o vencida);
- `sin_datos`: aún no tiene canario.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from html import escape

from terranova.catalogo import Catalogo
from terranova.vigilancia import DEGRADADOS, Resultado

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
        elif pasan == 0 and any(r.codigo not in DEGRADADOS for r in rs):
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


# Mismo lenguaje visual que el sitio (web/publico/estilo.css, que Caddy sirve en el mismo origen y
# trae Geist). El estilo de aquí basta solo: si /estilo.css no carga, la página sigue legible.
_ESTILO = """
:root{--fondo:#F6F7F4;--superficie:#ECEEE9;--tinta:#12261F;--suave:#4E5E57;--tenue:#56645E;
--linea:#D9DED6;--bosque:#0E2A22;--verde:#236E62;--ambar:#8F570B;--rojo:#A3362A;--gris:#8A958F;
--sans:Geist,"Helvetica Neue",system-ui,-apple-system,"Segoe UI",Arial,sans-serif;
--mono:"Geist Mono",ui-monospace,Consolas,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--tinta);font:400 16px/1.6 var(--sans);
-webkit-font-smoothing:antialiased}
a{color:inherit}
.env{max-width:1040px;margin:0 auto;padding:0 clamp(16px,4.5vw,56px)}
.e-cab{border-bottom:1px solid var(--linea);background:var(--fondo)}
.e-cab .env{display:flex;align-items:center;justify-content:space-between;gap:16px;height:64px}
.e-marca{display:inline-flex;align-items:center;gap:10px;font:700 18px/1 var(--sans);
letter-spacing:-.02em;text-decoration:none}
.e-marca svg{width:26px;height:26px}
.e-cab nav{display:flex;gap:4px;font-size:14.5px}
.e-cab nav a{text-decoration:none;color:var(--suave);padding:7px 12px;border-radius:3px}
.e-cab nav a:hover{background:var(--superficie);color:var(--tinta)}
.e-portada{padding:clamp(48px,7vw,88px) 0 32px}
.rotulo{font:500 14px/20px var(--sans);color:var(--tenue)}
h1{font:700 clamp(36px,5.4vw,58px)/1.04 var(--sans);letter-spacing:-.04em;margin:10px 0 14px}
.entrada{font-size:clamp(17px,1.5vw,19px);line-height:1.55;color:var(--suave);max-width:640px;
margin:0}
.e-meta{font:400 13px/20px var(--mono);color:var(--tenue);margin-top:18px}
.puerta{display:flex;gap:18px;align-items:center;background:var(--bosque);color:#F3EFE4;
border-radius:4px;padding:22px 26px;margin:8px 0 48px}
.puerta p{margin:0}.puerta .suave{color:#B9C6BF;font-size:14.5px}
.puerta .punto{width:12px;height:12px;background:#6CC3B3;box-shadow:0 0 0 6px rgba(108,195,179,.18)}
h2{font:700 clamp(24px,3vw,32px)/1.1 var(--sans);letter-spacing:-.03em;margin:0 0 10px}
.suave{color:var(--suave)}
.e-nota{font-size:15px;color:var(--suave);max-width:680px;margin:0 0 6px}
.e-cifras{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:24px 0 18px}
.e-cifra{background:var(--superficie);border:1px solid var(--linea);border-radius:3px;
padding:14px 16px}
.e-cifra b{display:block;font:700 30px/1.1 var(--sans);letter-spacing:-.03em}
.e-cifra span{font-size:13.5px;color:var(--suave)}
.punto{display:inline-block;flex:none;width:9px;height:9px;border-radius:50%;background:var(--gris)}
.verde .punto{background:var(--verde)}.ambar .punto{background:var(--ambar)}
.rojo .punto{background:var(--rojo)}
.e-cifra .punto{margin-right:6px}
.franja{display:flex;flex-wrap:wrap;gap:3px;margin:0 0 32px}
.franja i{width:11px;height:11px;border-radius:1px;background:var(--gris);opacity:.45}
.franja i.verde{background:var(--verde);opacity:1}.franja i.ambar{background:var(--ambar);opacity:1}
.franja i.rojo{background:var(--rojo);opacity:1}
ul{list-style:none;margin:0 0 64px;padding:0;border-top:1px solid var(--linea)}
li{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:baseline;
padding:14px 0;border-bottom:1px solid var(--linea)}
li .nombre{display:flex;gap:10px;align-items:baseline;min-width:0;overflow-wrap:anywhere}
li strong{font-weight:500}
li small{display:block;font-size:13.5px;color:var(--suave)}
li .lado{text-align:right;white-space:nowrap;font:400 12.5px/18px var(--mono);color:var(--tenue)}
.e-pie{background:var(--bosque);color:#B9C6BF;font:400 12.5px/20px var(--mono);padding:28px 0}
.e-pie .env{display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px}
.e-pie a{text-decoration:none;color:#F3EFE4;margin-right:16px}
@media (max-width:720px){.e-cifras{grid-template-columns:1fr 1fr}.e-cab nav a.op{display:none}
li{grid-template-columns:1fr;gap:2px}li .lado{text-align:left;white-space:normal;padding-left:19px}}
"""

_SIMBOLO = (
    '<svg viewBox="0 0 64 64" aria-hidden="true"><g fill="none" stroke="#0E2A22" stroke-width="4">'
    '<path d="M6 58V30a26 26 0 0 1 52 0v28"/><path d="M15 58V30a17 17 0 0 1 34 0v28"/></g>'
    '<path d="M24 58V30a8 8 0 0 1 16 0v28z" fill="#0E2A22"/>'
    '<circle cx="32" cy="46" r="3.5" fill="#E0A13A"/></svg>'
)


def pagina_estado(ultimos: list[Resultado], catalogo: Catalogo, ahora: datetime) -> str:
    fuentes = estado_fuentes(ultimos, catalogo, ahora)
    cuenta = {e: sum(f["estado"] == e for f in fuentes) for e in ORDEN}
    ultima = max((f["ultimo"] for f in fuentes if isinstance(f["ultimo"], datetime)), default=None)
    verificacion = _hora(ultima) if ultima else "todavía no hay canarios registrados"
    cifras = "".join(
        f'<div class="e-cifra {e}"><b>{cuenta[e]}</b><span><span class="punto"></span>'
        f"{ETIQUETA[e]}</span></div>"
        for e in ORDEN
    )
    # una casilla por fuente, en el mismo orden que la lista: la foto de un vistazo
    franja = "".join(
        f'<i class="{f["estado"]}" title="{escape(str(f["titulo"]))}"></i>' for f in fuentes
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
            f'<li class="{estado}"><span class="nombre"><span class="punto"></span><span>'
            f"<strong>{escape(str(f['titulo']))}</strong>"
            f"<small>{escape(str(f['entidad']))} · {ETIQUETA[estado]}</small></span></span>"
            f'<span class="lado">{escape(detalle)}</span></li>'
        )
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Estado del servicio · Terrnova</title>
<meta name="description" content="La puerta y cada fuente oficial según su último canario.">
<meta name="theme-color" content="#F6F7F4">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/estilo.css">
<style>{_ESTILO}</style>
</head>
<body>
<header class="e-cab"><div class="env">
<a class="e-marca" href="/" aria-label="Terrnova, inicio">{_SIMBOLO}Terrnova</a>
<nav aria-label="Principal"><a class="op" href="/fuentes">Fuentes</a>
<a class="op" href="/desarrolladores">Desarrolladores</a><a href="/contacto">Contacto</a></nav>
</div></header>
<main class="env">
<section class="e-portada">
<span class="rotulo">Estado del servicio</span>
<h1>Estado de Terrnova</h1>
<p class="entrada">Solo lo que se mide: el último canario de cada fuente y su hora. No hay
histórico de disponibilidad, así que aquí no hay porcentajes.</p>
<p class="e-meta">Generada el {_hora(ahora)} · datos en JSON:
<a href="/v1/estado">/v1/estado</a></p>
</section>

<section class="puerta verde">
<span class="punto"></span>
<div><p><strong>La puerta responde</strong></p>
<p class="suave">Esta página la sirve la misma puerta que atiende la API y el MCP: si la ve, la
puerta está en línea.</p></div>
</section>

<h2>Fuentes oficiales</h2>
<p class="e-nota">Cada fuente se prueba a diario con un canario: una consulta con una respuesta
conocida, medida en la fuente. Última verificación: {verificacion}.</p>
<p class="e-nota">Las fuentes son de terceros (entidades públicas). Si una falla, la puerta responde
«no se pudo» y no inventa el dato.</p>
<div class="e-cifras">{cifras}</div>
<div class="franja" aria-hidden="true">{franja}</div>
<ul>
{chr(10).join(filas)}
</ul>
</main>
<footer class="e-pie"><div class="env">
<span><a href="/">Inicio</a><a href="/fuentes">Fuentes</a><a href="/precios">Precios</a><a
href="/terminos">Términos</a></span>
<span>© 2026 Terrnova · terrnova.com</span>
</div></footer>
</body>
</html>
"""
