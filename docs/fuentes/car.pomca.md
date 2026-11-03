# CAR Cundinamarca: POMCA (`car.pomca_zonificacion`, `car.pomca_rio_sumapaz`, `car.pomca_rio_bogota`)

Es la zonificación ambiental de los Planes de Ordenación y Manejo de Cuenca (POMCA) que adoptó la
CAR. Está en ArcGIS Online, un servicio por cuenca, y se consulta en vivo por punto. Es
determinante ambiental del POT: para un lote pesa tanto como el POT.

| Fuente | Capas | Licencia | Herramientas |
|---|---|---|---|
| `car.pomca_zonificacion` | nueve cuencas: río Bogotá, Carare-Minero, Garagoa, río Negro, Alto Suárez, Medio y Bajo Suárez, río Seco, Guavio, Guayuriba | CC BY 4.0 | `car_pomca_en_punto` |
| `car.pomca_rio_sumapaz` | Sumapaz (Res. 149 de 2023) | sin licencia declarada → CC BY-SA 4.0 (ADR-0019) | `car_pomca_rio_sumapaz_en_punto` |
| `car.pomca_rio_bogota` | río Bogotá (Res. 957 de 2019) | CC BY 4.0 | ninguna (borrador desde el 2026-11-03) |

## Qué publica

Por polígono:

- la categoría de ordenación: conservación y protección ambiental, o uso múltiple;
- la zona de uso y manejo;
- la subzona, con su sigla (ZU, ARUM, UM1, CP-APi…).

## Campos que importan

- Cada capa nombra distinto los mismos campos: `CAT_ORD`, `CAT_ORD_A` o `CATEGORIA`. La fuente los
  une con alias.
- `NOMENCLAT`, la sigla, queda en blanco en parte del río Negro y del Alto Suárez. En el río Bogotá
  puede ser un nombre («Areas SINAP»).
- `DESCRIP` **no es uniforme**:
  - en el Guayuriba y el Garagoa describe la subzona;
  - en el río Bogotá repite la sigla;
  - en el río Negro y el Alto Suárez trae notas del método: «Cultivos Permanentes
    SemiintensivosIUAAlto», «Capacidad uso, Validacion por conflicto del suelo*».

## Cobertura

Las diez cuencas con POMCA de la jurisdicción de la CAR. Un punto cae en una sola. Medina no cae en
ninguna.

## Trampas medidas

1. **Dos herramientas para la misma pregunta.** `car_pomca_rio_bogota_en_punto` daba lo mismo que
   `car_pomca_en_punto` en la cuenca del río Bogotá, pero sin decir la cuenca.
2. **El vacío sin salida.** En Fusagasugá (cuenca del Sumapaz), la herramienta general decía
   «no encontrado» sin remitir a la del Sumapaz.
3. **La descripción como ruido.** Ver `DESCRIP` arriba.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `car_pomca_en_punto` | medio → alto | v2: sin `descripcion`; su vacío remite al Sumapaz |
| `car_pomca_rio_sumapaz_en_punto` | medio | v2: su vacío remite a las otras nueve cuencas |
| `car_pomca_rio_bogota_en_punto` | — | retirada el 2026-11-03 |

## Decisiones

- **2026-11-03, patrón F de la revisión de valor:**
  - Se retira `car_pomca_rio_bogota_en_punto` y su fuente pasa a borrador.
  - El Sumapaz no se suma a la herramienta general: su licencia no está declarada y se trata como
    BY-SA. Mezclarla con capas CC BY borraría esa diferencia. Va aparte, y cada vacío remite al
    otro.
  - `DESCRIP` sale de la lista blanca.
- **Pendiente:**
  - devolver la geometría de la zona; un polígono pesa decenas de KB, así que habría que
    simplificarla;
  - las rondas hídricas (`car.rondas_delimitadas`).
