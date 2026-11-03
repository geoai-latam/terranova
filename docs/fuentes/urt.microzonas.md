# URT · zonas microfocalizadas para la restitución de tierras

La fuente es `urt.microzonas`. Las herramientas son `urt_microzona_en_punto` y
`urt_microzona_en_poligono`.

## Qué publica

- La Unidad de Restitución de Tierras publica las zonas donde puede tramitar solicitudes de
  restitución (Ley 1448 de 2011, art. 76; Decreto 4829 de 2011).
- El ítem `Open_Data_Microzonas` está en su ArcGIS Online, capa 3: un polígono por microzona, con su
  resolución vigente y su estado.
- Licencia CC BY-SA 4.0, según la ficha del ítem.
- **Solo la zona.** Las solicitudes y las sentencias por predio llevan a víctimas con nombre y quedan
  fuera (ADR-0014).

## Campos

| Capa | rt/1 | Nota |
|---|---|---|
| `id_microzona` | `id_microzona` | único |
| `cod_dane`, `mpio`, `depto` | `municipio_registrado_divipola`, `municipio_registrado`, `departamento_registrado` | el municipio con que la URT registró la zona, no el del punto (trampa 1) |
| `n_res_m`, `fecha_res_vigente` | `resolucion`, `fecha_resolucion` | la resolución vigente |
| `estado_micro` | `estado` | En firme o Cerrada |
| `territorial` | `territorial` | la dirección territorial que la atiende |
| (cálculo) | `area_ha` | solo por polígono: hectáreas de la microzona dentro del polígono, en PostGIS |

## Cobertura medida (copia del 2026-11-02)

- 1 314 microzonas: 924 en firme y 390 cerradas.
- 665 municipios registrados y 24 territoriales.
- Tamaño:
  - mediana de 16 388 ha; percentil 10, 403 ha; percentil 90, 100 065 ha;
  - 592 pasan de 20 000 ha;
  - la mayor, la 1506 de «Puerto Alegría» (Amazonas), tiene 10,7 millones de ha.

## Trampas medidas

1. **El municipio es el del registro, no el del lote** (hallazgo #16 de GEO Copilot; 2026-11-03).
   - La 609 se registra como «Cajicá» y tiene 65 170 ha. Cubre el centro de Chía, Fonquetá, Tabio y
     Zipaquirá.
   - Un lote en Chía sale «en una microzona de Cajicá».
   - Confirmado en vivo en la capa 3 con el punto (−74.0585, 4.8615): `mpio: Cajicá`.
2. **Estar en una microzona no dice que el predio tenga solicitud.** Dice que la URT puede tramitarlas
   ahí.
3. **Arranque en frío de la capa alojada.** La primera consulta tarda de 17 a 31 s y las siguientes
   0,5 s. Por eso va por copia, que responde en 10 ms.

## Decisiones

- **Por copia** (ADR-0024). Por polígono (ADR-0035), el cruce coincide con la capa en 6 lotes.
- **v2 de las dos herramientas, 2026-11-03.**
  - Los campos pasan a `municipio_registrado`, `municipio_registrado_divipola` y
    `departamento_registrado`, y la descripción da el caso de la 609. El nombre dice qué es: el
    municipio con que la URT registró la zona.
  - Por polígono:
    - suma `area_ha` por microzona, de la mayor a la menor, y `area_ha_total`;
    - unas hectáreas mínimas dicen que el lote apenas roza la zona;
    - el lote de 0,003° × 0,003° en Chía da 11,04 ha, todas dentro de la 609;
    - el canario del Cauca da 4 microzonas y 5 533,99 ha.
  - El área se calcula en PostGIS, sobre la copia, y la capa no la publica. Por eso el canario no
    fija hectáreas: solo el total de microzonas, medido en la capa.
