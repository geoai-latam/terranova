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
| `car_pomca_en_punto` | medio → alto | v3: sin `descripcion`; su vacío remite al Sumapaz; polígono simplificado |
| `car_pomca_rio_sumapaz_en_punto` | medio | v3: su vacío remite a las otras nueve cuencas; polígono simplificado |
| `car_pomca_rio_bogota_en_punto` | — | retirada el 2026-11-03 |

## Decisiones

- **2026-11-03, patrón F de la revisión de valor:**
  - Se retira `car_pomca_rio_bogota_en_punto` y su fuente pasa a borrador.
  - El Sumapaz no se suma a la herramienta general: su licencia no está declarada y se trata como
    BY-SA. Mezclarla con capas CC BY borraría esa diferencia. Va aparte, y cada vacío remite al
    otro.
  - `DESCRIP` sale de la lista blanca.
- **2026-11-03, geometría:** las dos herramientas devuelven el polígono de la zona simplificado
  (~55 m, `geometria: simplificada`). Medido en la fuente:

  | Punto | Completo | Simplificado |
  |---|---|---|
  | Bogotá urbana (río Bogotá, ZU) | 816 KB, 22 725 vértices | 21 KB, 1 077 |
  | Chía rural (río Bogotá, ARUM) | 34 KB, 950 | 1 KB, 64 |
  | río Negro (agrosilvopastoril) | 610 KB, 16 991 | 7 KB, 356 |
  | Quetame (Guayuriba, UM1) | 123 KB, 3 429 | 1 KB, 51 |

  Responden en 1 a 3 s. Sirve para ver la zona en un mapa, no para medir linderos: lo dice la
  descripción.
- **Pendiente:** una herramienta por polígono (área de cada zona dentro de un lote). Pide copiar
  las ~550 000 zonas.
- Las rondas hídricas tienen su propia ficha: [car.rondas_delimitadas.md](car.rondas_delimitadas.md).
