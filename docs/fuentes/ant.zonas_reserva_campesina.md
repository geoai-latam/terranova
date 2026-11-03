# ANT: zonas de reserva campesina constituidas (`ant.zonas_reserva_campesina`)

Las zonas de reserva campesina (ZRC) que ha constituido la Agencia Nacional de Tierras. Están en un
servicio ArcGIS de la ANT, publicado por el proxy de ArcGIS Online, con licencia CC BY-SA 4.0. Se
consulta en vivo, por punto.

## Qué publica

Medido el 2026-11-03, son 30 polígonos, uno por zona. Cada uno trae:

- nombre;
- departamento y municipios, en texto;
- acto de constitución;
- fecha;
- área en hectáreas.

`TIPO_ACTO` es un código sin dominio publicado y no entra.

## Campos que importan

- `FECHA_CONSTITUCION` es **texto d/m/aaaa** en las 30 zonas: «7/11/2000» es el 7 de noviembre.
  Lo confirma el acto, la Resolución 046 de 2000.
- Dos zonas le pegan la modificación al mismo campo:
  - Cuenca de Río Pato y Valle de Balsillas: «18/12/1997 Fecha de modificación: 26/09/2024»;
  - La Tuna: «12/12/2022 Fecha de modificación: 10/12/2024».

  El acto lo repite: «… modificado por el Acuerdo 389 de 2024».

## Cobertura

Todo el país, solo las zonas ya constituidas: de 1997 (Guaviare) a agosto de 2026 (Río Cafre,
Cumanday). Las que están en trámite no están.

## Trampas medidas

1. **El vacío falso.** El proxy responde vacío sin error cerca del 25 % de las veces (4 de 16, el
   2026-10-23). La fuente reintenta 3 veces antes de decir «no encontrado» y lo avisa.
2. **La fecha ambigua.** «7/11/2000» se puede leer como 11 de julio.
3. **Dos fechas en un campo.** Ver arriba.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `ant_zonas_reserva_campesina_en_punto` | medio | v2: `fecha_constitucion` en ISO y `fecha_modificacion` aparte |

## Decisiones

- **2026-11-03, patrón I de la revisión de valor:**
  - `fecha_constitucion` pasa a `date` con `orden_fecha: dma`. El motor toma la primera fecha
    aunque venga texto detrás.
  - `fecha_modificacion` sale de un derivado `columna` con `patron` (`modificaci[oó]n:\s*(fecha)`)
    y `orden_fecha`, dos opciones nuevas del motor.
  - Medido en producción:

    | Zona | Constitución | Modificación |
    |---|---|---|
    | Cabrera | 2000-11-07 | — |
    | Río Pato | 1997-12-18 | 2024-09-26 |
    | La Tuna | 2022-12-12 | 2024-12-10 |

- **Pendiente:** pasarla a copia. Son 30 polígonos: la copia sería instantánea y sin vacíos falsos.
