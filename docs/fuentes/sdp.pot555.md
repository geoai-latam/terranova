# SDP Bogotá: POT 555, tratamiento urbanístico y área de actividad (`sdp.pot555_tratamiento`, `sdp.pot555_area_actividad`)

Son dos capas del Plan de Ordenamiento Territorial de Bogotá (Decreto 555 de 2021). Las publica la
Secretaría Distrital de Planeación en su servidor ArcGIS (`POT555/NORMA_URBANÍSTICA_Y_OT`), con
licencia CC BY 4.0.

| Fuente | Capa | Copia | Herramientas |
|---|---|---|---|
| `sdp.pot555_tratamiento` | 2 | `sdp_pot555_tratamiento` | `sdp_tratamiento_urbanistico_en_punto`, `sdp_tratamiento_urbanistico_en_poligono` |
| `sdp.pot555_area_actividad` | 9 | `sdp_pot555_area_actividad` | `sdp_area_actividad_en_punto`, `sdp_area_actividad_en_poligono` |

## Qué publica

- **Tratamiento urbanístico:** cómo se puede transformar cada zona. Son cinco: consolidación,
  renovación, desarrollo, conservación y mejoramiento integral. Trae la altura máxima en pisos, la
  tipología y el subtratamiento.
- **Área de actividad:** qué usos del suelo admite cada zona. Hay de proximidad, estructurante y de
  grandes servicios metropolitanos, cada una con sus variantes («receptora de vivienda de interés
  social», «generadora de soportes urbanos»…).

Las dos son la norma general. Un predio puede tener además normas específicas: planes parciales,
bienes de interés cultural o PEMP.

## Campos que importan

- `ALTURA_MAXIMA` es texto. Puede ser un número («7»), un rango («8-11») o una remisión a otra norma
  («PEMP», «F2», «BIC NAL»). La renovación no la trae, porque la define su plan.
- `TIPOLOGIA`: «TA» (aislada) o vacío.
- `NUMERO_ACTO_ADMINISTRATIVO` y `FECHA_ACTO_ADMINISTRATIVO`: casi todo es el 555 de 2021, pero ya
  hay piezas de actos posteriores. Por ejemplo, el 1094 del 2026-05-26, en la franja del canario.

## Cobertura

- Todo el suelo de Bogotá. Las dos capas cubren un lote entero: en un lote de 4,91 ha en Chapinero,
  las piezas de cada capa suman 4,91 ha.
- El servidor de la SDP no responde a la IP del centro de datos. La copia se rehace desde Colombia,
  a mano (vigente: 2026-10-28).

## Trampas medidas

1. **Una pieza no es un tratamiento.** La capa trae un polígono por cada combinación de tratamiento,
   altura y tipología. En la franja del canario, de unas 393 ha, hay 99 piezas:
   - consolidación, 174 ha;
   - renovación, 114 ha;
   - conservación, 58 ha.

   Con solo la lista no se sabía cuánto pesa cada una.
2. **Tocar no es pesar.** Una pieza que roza el lote sale igual que la que lo cubre. En Kennedy, la
   actividad de grandes servicios metropolitanos toca el lote con 0,02 ha de 30,7.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `sdp_tratamiento_urbanistico_en_poligono` | bajo → alto | v2: hectáreas de cada pieza dentro del polígono, de la mayor a la menor, con el total |
| `sdp_area_actividad_en_poligono` | bajo → alto | v2: lo mismo, para el área de actividad |

## Decisiones

- **2026-11-03, patrón E de la revisión de valor:**
  - El motor de copias suma `area_en_poligono`. Cada elemento trae `_area_ha`: las hectáreas
    geodésicas de su intersección con el polígono. Se puede ordenar por esa columna.
  - Las dos herramientas en polígono van de la pieza mayor a la menor, con `area_ha` y
    `area_ha_total`.
  - Se dejan las piezas, no se agrupan: cada una trae su geometría para el mapa y su altura.
