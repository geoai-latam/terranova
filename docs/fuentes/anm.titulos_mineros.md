# ANM: títulos mineros con explotador autorizado en el RUCOM (`anm.titulos_mineros`)

El conjunto «RUCOM Explotador Minero Autorizado — Título Minero» de la Agencia Nacional de Minería,
en datos.gov.co (`42ha-fhvj`), con licencia CC BY-SA 4.0. Se consulta en vivo.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `anm.titulos_mineros` | `42ha-fhvj` | `anm_titulos_municipio`, `anm_titulo_por_expediente` |

## Qué publica

Los títulos mineros cuyo explotador está inscrito en el RUCOM (Registro Único de Comercializadores
de Minerales). Cada fila tiene el expediente, el mineral, el municipio (código DANE), el
departamento, la planta de beneficio y el titular.

**No es el catastro minero.** Un título sin explotador inscrito en el RUCOM no aparece aquí. El
catastro completo, con los polígonos, está en AnnA Minería, que pide inicio de sesión (ADR-0018).

## Campos que importan

- `codigo_expediente`: un título puede salir en varias filas, una por mineral.
- `mineral`: texto libre de la fuente. El mismo mineral sale de varias formas:
  - `ORO`, `ORO ALUVION`, `ORO VETA`, `MINERALES DE ORO Y SUS CONCENTRADOS`…;
  - `CARBON` y `CARBÓN COQUIZABLE O METALURGICO`, con y sin tilde.
  - En todo el país hay 177 formas distintas.
- `codigo_dane`: el DIVIPOLA del municipio, en 5 dígitos.
- `nombre_persona` (el titular): puede ser una persona natural y no hay columna que lo distinga. No
  sale (ADR-0014).

## Cobertura

Medido el 2026-11-03:

- 2 807 títulos distintos en 668 municipios;
- la última carga es del 2026-03-18, aunque la fuente declara una actualización trimestral (la
  puerta avisa que los datos no son recientes);
- La Calera (25377): 0;
- Yumbo (76892): 29 títulos;
- Medellín (05001): 12.

## Trampas medidas

1. **«0» no es «sin minería».** GEO Copilot leyó 0 títulos en La Calera como si no hubiera minería.
   Lo que dice el 0 es que ningún título del municipio tiene un explotador inscrito en el RUCOM.
2. **Sumar por mineral cuenta dos veces.** Un título que ampara arcilla y arena cuenta en los dos.
   El total del municipio sale de `count(distinct codigo_expediente)`.
3. **Las variantes del mineral no se juntan.** Juntarlas sería interpretar a la ANM. La descripción
   lo advierte.
4. **El orden alfabético ponía primero lo menos importante.** En Yumbo salía primero ARCILLA, con 1
   título, antes que los materiales de construcción, que tienen 12.
5. **Una fila por explotador, y filas repetidas.** Cada fila de un expediente es un explotador
   autorizado de un mineral: ABQ-101 tiene 8 filas, 4 explotadores distintos por cada uno de sus
   dos minerales. Pero 2 859 combinaciones de expediente, mineral y explotador salen más de una
   vez: 3 395 de las 12 914 filas sobran (medido el 2026-11-03). Contar filas no es contar
   explotadores.
6. **Un expediente con 177 explotadores.** ARE-TGJ-14151 (oro, Timbiquí) tiene 177 y
   ARE-TGJ-08002X, 176. Un título puede cruzar municipios: 2614T (carbón) está en Durania y en San
   Cayetano.
7. **Sin vigencia, área ni polígono.** El conjunto tiene solo siete columnas: expediente, mineral,
   planta de beneficio, municipio, departamento, código DANE y nombre del explotador.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `anm_titulos_municipio` | medio | v2: del mineral con más títulos al que menos; `titulos_total` sin doble conteo; `minerales`; descripción y vacío que dicen qué cubre el RUCOM |
| `anm_titulo_por_expediente` (v2) | medio → alto | explotadores distintos por mineral y en total; dice que no trae vigencia, área ni polígono |

## Decisiones

- **2026-11-03, hallazgo #9 de GEO Copilot y revisión de valor:**
  - La descripción y la pregunta dicen que son los títulos con explotador autorizado en el RUCOM,
    no todos.
  - El vacío lo explica y nombra AnnA Minería, que no está en Terrnova.
  - Hay un complemento con el total de títulos distintos del municipio.
- **2026-11-03, revisión de valor (`anm_titulo_por_expediente` v2):**
  - `registros` (filas, con repetidas) pasa a `explotadores`, que cuenta nombres distintos por
    mineral. Contar no expone ningún nombre (ADR-0014). Un complemento da `explotadores_total` del
    título, y `minerales` cuenta los minerales.
  - Ordena del mineral con más explotadores al que menos.
  - Un aviso, con datos, dice qué significa estar aquí y que no hay vigencia, área ni polígono. El
    vacío dice que no quiere decir que el título no exista.
- **Pendiente (plan de producto, B6):** buscar una capa pública de títulos de la ANM con polígono y
  sin inicio de sesión.
