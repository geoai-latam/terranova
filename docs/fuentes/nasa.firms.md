# nasa.firms · Focos de calor de NASA FIRMS por periodo

Herramienta: `nasa_firms_focos_en_zona`, por rectángulo y periodo de hasta 31 días, desde 2012.

## De dónde sale

- API por área de FIRMS: `firms.modaps.eosdis.nasa.gov/api/area/csv/<MAP_KEY>/<producto>/<oeste,sur,este,norte>/<días>/<fecha>`.
  - Acepta hasta 5 días por petición, así que un periodo de 31 días son 7 peticiones.
  - La MAP_KEY es gratis y va en el `.env` de la VPS (`FIRMS_MAP_KEY`). Solo la lee `amenazas-mcp`
    y nunca sale en errores, hechos ni respuestas grabadas.
- Cada tramo va al producto estándar (`VIIRS_SNPP_SP`, definitivo) si su fecha ya está en él, o al
  casi en tiempo real (`VIIRS_SNPP_NRT`) si no. Un tramo no cruza de uno al otro.
  - Medido con `data_availability` el 2026-11-05: el SP llega hasta el 2026-07-31 y el NRT empieza
    el 2026-08-01.
- Licencia: CC0 1.0, según la política de datos de Earthdata.

## Lo medido (2026-11-05)

- Del 2024-02-01 al 2024-02-05, en [-79.1, -4.3, -66.8, 13.5]: 2 498 focos.
  - Por día: 1 246, 565, 228, 283 y 176.
  - Por confianza: n 2 363, l 76, h 59.
- Canario: el 2024-02-01 en la Orinoquía ([-72, 3, -67.5, 7]) hay 182 focos. Es un dato del
  producto estándar, que no cambia.
- Códigos:
  - La confianza de VIIRS sale como l, n o h. La documentación dice «low, nominal and high».
  - Día o noche: D o N.
  - El producto estándar trae `type`, pero FIRMS documenta sus valores (0 a 3) solo para MODIS.
    En VIIRS sale sin significado.
- La hora (`acq_time`) viene sin ceros a la izquierda: «623» es 06:23 UTC. Sale como la publica
  FIRMS.

## Cuidado al leerlo

- Un incendio grande da muchos focos. Contar focos no es contar incendios.
- No todo foco es un incendio de vegetación.
- El satélite pasa dos veces al día y no ve bajo nubes densas. «Sin focos» no garantiza que no
  hubo fuego, y el aviso de vacío lo dice.
- Los últimos 7 días sin llave (CSV regional) siguen en `amenazas_incendios`, dentro del conector.
