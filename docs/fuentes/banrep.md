# Banco de la República: TRM, tasa de política, IBR, DTF y UVR (`banrep.*`)

Cinco series del servicio SDMX oficial del BanRep (`totoro.banrep.gov.co`), en vivo. Se citan con
la fecha de consulta, como pide el aviso legal del Banco. Herramientas: `banrep_<serie>_recientes`
(valor alto), con las últimas N observaciones por serie.

## Lo medido (2026-11-05)

- **TRM:** trae la de mañana y los fines de semana. 3221,19 el 2026-11-05.
- **Tasa de política:** 12,25 % y trae los fines de semana.
- **DTF:** es semanal y sale una fila por día de su semana de vigencia. El 2026-11-05 llegaba
  hasta el 2026-11-08.
- **IBR:** cuatro series (IRIBRM00, 01, 03 y 06) por dos unidades (ER y NR): `ultimas: 3` da
  24 filas. El mismo día ER sale más alta que NR (12,252 frente a 11,401 en IRIBRM00).
- **UVR:** dos filas por fecha con la misma serie (RVU). CRVU es el valor en pesos (421,2214 el
  2026-11-15) y APC, la variación en porcentaje (6,3). Va calculada hasta el 15 del mes siguiente.
- **Tabla de códigos:** el servicio no deja leer las estructuras SDMX (dataflow con
  `references`). Responde «Unauthorized Request Blocked», un antibots, desde Colombia y desde la
  VPS. No se fuerza. Por eso los códigos de unidad no llevan `codigos`, que exige una tabla
  publicada.

## Decisiones

- Avisos en IBR y UVR que explican cuántas filas salen por fecha y qué distingue la unidad, con
  los valores medidos. Lo que no se pudo leer en la tabla oficial se dice como medido, no como
  definición.
