# IGAC, capacidad de uso de las tierras (`igac.agrologia.capacidad_uso`)

La capa nacional de capacidad de uso de las tierras de la Subdirección de Agrología del IGAC, a
escala 1:100.000 (capa 0, `Correlación_Capacidad_Uso_100k`, del MapServer de agrología). Licencia
CC BY 4.0 por la Resolución 616 de 2020, art. 7: el ítem del servicio trae la licencia vacía.

## Qué publica

Un polígono por unidad cartográfica, con:

- `UCCapacida`: la unidad. Es la clase (1 a 8) con sus limitantes en letras: `4sc` es clase 4
  con limitantes de suelo y clima.
- `Descripcio`: la descripción («Capacidad agrícola y pecuaria»).
- El agua (`CA`) y lo urbano (`ZU`) no tienen clase agrológica. La herramienta dice qué son en
  `unidad_capacidad_significado`.
- `Area`: no declara la unidad, así que queda fuera.

## Cómo se sirve

De la copia de Terrnova en PostGIS (ADR-0024), simplificada a ~11 m. En vivo, un punto tardaba
~50 s desde el servidor (medido el 2026-10-27). La copia es del 2026-10-27.

## Trampas medidas

1. **Una unidad viene en varios pedazos.** En la franja del canario, `2c` sale en dos polígonos
   (188,9 y 75,7 ha) y `6p` en otros dos. Sin sumar, parecían filas repetidas.
2. **Escala 1:100.000.** No sirve para un predio: un borde puede correrse cientos de metros.
3. **Áreas dentro del polígono:** las calcula la copia sobre la geometría simplificada.
   Contrastadas el 2026-11-03 con el área del polígono pedido:

   | Polígono | Área esperada | Suma de la herramienta |
   |---|---|---|
   | Franja del canario (paralelogramo de 0,04° × 0,004°) | ~395 ha | 392,65 ha |
   | Cuadro de 0,1° en el Meta | ~12 300 ha | 12 278,62 ha, en 6 unidades |

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `igac_capacidad_uso_en_punto` | alto | unidad, descripción y significado |
| `igac_capacidad_uso_en_poligono` | medio → alto | `area_ha` por pedazo, `area_ha_por_unidad` y `area_ha_total` |

## Decisiones

- **2026-11-03, revisión de valor (v3 del polígono):** «filas repetidas sin porcentaje».
  - Cada pedazo trae `area_ha` dentro del polígono, el mayor primero.
  - `area_ha_por_unidad` las suma por unidad, y `area_ha_total` da el total.
  - El porcentaje sale de esos dos. No se calcula en la puerta porque no hay un derivado de
    porcentaje; los de las SDP siguieron el mismo camino.
