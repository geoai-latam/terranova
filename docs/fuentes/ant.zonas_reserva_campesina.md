# ANT: zonas de reserva campesina constituidas (`ant.zonas_reserva_campesina`)

Las zonas de reserva campesina (ZRC) que ha constituido la Agencia Nacional de Tierras. Están en un
servicio ArcGIS de la ANT, publicado por el proxy de ArcGIS Online, con licencia CC BY-SA 4.0. Desde el 2026-11-03 se
consulta en una copia de Terrnova (30 polígonos), por punto.

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
   2026-10-23).
   - En vivo había que reintentar 3 veces antes de decir «no encontrado», y un vacío tardaba
     2-3 s.
   - La copia lo resuelve: el vacío es real y responde en ~10 ms.
   - La copia se protege del mismo vacío. Compara con el conteo de la capa, y una descarga sin
     filas no reemplaza la copia vigente.
2. **La fecha ambigua.** «7/11/2000» se puede leer como 11 de julio.
3. **Dos fechas en un campo.** Ver arriba.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `ant_zonas_reserva_campesina_en_punto` | medio | v3: sobre la copia, con aviso de vacío y área con dos decimales |
| `ant_zonas_reserva_campesina_en_poligono` | alto | v1: «¿este lote cae en una ZRC?», con las hectáreas dentro del lote |
| `ant_zonas_reserva_campesina_en_zona` | medio | v1: por rectángulo; para pintar la capa |

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

- **2026-11-03, copia (v3):**
  - **Origen y frescura:** origen `arcgis`, capa 0, clave `OBJECTID_1`. El SLA es de 3 meses, así
    que se rehace cada mes y medio: la ANT constituyó dos zonas en agosto de 2026.
  - **Fechas día/mes:** `FECHA_CONSTITUCION` se guarda como texto. Postgres leería «7/11/2000»
    como 11 de julio, y el derivado de la modificación necesita lo que viene detrás. Es una regla
    del motor: un campo con `orden_fecha` se copia como texto y el ejecutor lo pasa a ISO al
    responder.
  - **Avisos:** el vacío avisa que las zonas en trámite no están en la fuente.
  - **Medido en producción:**
    - Cabrera, el canario: 2000-11-07.
    - Río Pato: 1997-12-18, modificada el 2024-09-26, igual que en la fuente en vivo.
    - La Tuna: 2022-12-12, modificada el 2024-12-10.
    - Río Cafre: 2026-08-04.
    - Bogotá: «no encontrado», con el aviso, en 10 ms.
  - **Reintentos:** la prueba de `reintentos_si_vacio` pasó a los resguardos, que siguen en vivo
    por el mismo proxy.
- **2026-11-05, por polígono y por zona:** dos herramientas sobre la misma copia, sin reingerirla.
  No hay herramienta por municipio: `MUNICIPIOS` trae nombres sueltos, no códigos DIVIPOLA. Medido
  en la fuente (returnCountOnly): 2 en la franja Cabrera-Sumapaz y 4 en [-75, 3, -73, 5]. La prueba
  de `reintentos_si_vacio` pasó a la UAF (`ant_uaf_en_punto`), la única de la ANT que sigue en vivo
  por ese proxy.
