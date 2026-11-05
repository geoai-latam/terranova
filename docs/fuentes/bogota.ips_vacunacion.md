# Bogotá: IPS con servicio de vacunación

Fuente `bogota.ips_vacunacion`. Herramienta: `bogota_vacunacion_en_zona`.

## Qué es

Las sedes de instituciones prestadoras de salud (IPS) con servicio de vacunación en Bogotá, como
las publica la Secretaría Distrital de Salud (SDS). Un punto por sede, públicas y privadas.

- **Capa:** `serviciosgis.catastrobogota.gov.co/arcgis/rest/services/salud/puntosdevacunacion/MapServer/1`
  (la capa 0 del mismo servicio son los puntos de fiebre amarilla).
- **Copia:** se baja a mano desde Colombia, porque la VPS no llega a los servidores del Distrito.
  Es una copia espacial en la tabla `bogota_ips_vacunacion`.
- **Herramienta:** por rectángulo, con el punto, el código de sede del REPS, el nombre, el
  prestador, la dirección, la naturaleza y la localidad.
- **Cruce:** el código de sede es el del REPS, así que se cruza con `minsalud_sedes_salud_*`.

## Licencia

Paquete `instituciones-prestadoras-de-salud-con-servicio-de-vacunacion` del portal
datosabiertos.bogota.gov.co, que apunta a la capa 1: `license_id: CC-BY-4.0`. Verificada el
2026-11-05 en
<https://datosabiertos.bogota.gov.co/api/3/action/package_show?id=instituciones-prestadoras-de-salud-con-servicio-de-vacunacion>.

## Lo medido (2026-11-05)

- **Filas:** 308 sedes: 231 privadas y 77 públicas. Todas traen punto.
- **Código de sede del REPS:** único en las 308. `IDENTIFICA` repite 40 valores y no se copia.
- **Localidad:** código con el dominio «locasalud» publicado en la capa (1 Usaquén … 20 Sumapaz).
- **Proyección:** la capa está en EPSG:3857; la copia pide EPSG:4326.
- **Campos que no se copian:**
  - `CLASE_DE_P`: es la misma en todas («Instituciones Prestadoras de Servicios de Salud - IPS»);
  - `CORREO_ELE`: 14 sedes traen una cuenta de gmail.
- **Texto roto en la fuente:** algunos nombres traen la «í» rota (p. ej. «José María Carbonell»).
- **Fecha:** el paquete se tocó por última vez el 2025-07-29. La herramienta avisa que se
  confirmen horarios y vacunas con la sede.
- **Canario:** 14 sedes en [-74.09, 4.6, -74.06, 4.63] (13 privadas y 1 pública), medidas en la
  capa.

## Lo que no trae

- Las jornadas y brigadas de vacunación, que no son sedes de IPS.
- Las vacunas que aplica cada sede y sus horarios.
- El resto del país.
