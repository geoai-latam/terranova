# Bogotá: puntos, tramos y zonas críticas de siniestralidad vial (SDM)

Fuente `sdm.siniestralidad_critica`. Herramienta: `sdm_siniestralidad_critica_en_zona`.

## Qué es

El análisis de sitios críticos de siniestralidad 2022-2025 de la Oficina de Seguridad Vial de la
Secretaría Distrital de Movilidad (SDM). Son veinte capas del folder `DatosAbiertos` de
`sig.simur.gov.co/arcgis/rest/services`, una por elemento, actor vial y red. Van en una copia
espacial (ADR-0024) con una columna `tipo`, como «punto crítico · motociclistas · vía arterial».

| Elemento | Peatones | Ciclistas | Motociclistas | Vulnerables | Total |
|---|---|---|---|---|---|
| Punto, vía arterial | 10 | 11 | 3 | 21 | 45 |
| Punto, vía no arterial | 11 | 16 | 38 | 46 | 111 |
| Tramo, vía arterial | 15 | 15 | 12 | 23 | 65 |
| Tramo, vía no arterial | 11 | 12 | 27 | 36 | 86 |
| Zona, vía no arterial | 21 | 13 | 17 | 15 | 66 |

Son 373 sitios, contados el 2026-11-05. «Vulnerables» junta a peatones, ciclistas y
motociclistas. Cada sitio trae los fallecidos y lesionados de su actor vial en esos cuatro años:
son totales por sitio, sin víctimas ni siniestros uno por uno (ADR-0014).

- **Copia:** se baja a mano desde Colombia, porque la VPS no llega a `sig.simur.gov.co`. Las
  veinte capas se bajaron en una pasada, una petición a la vez.
- **Sumas:** la herramienta suma fallecidos y lesionados por actor vial solo en los puntos. Un
  punto puede quedar dentro de un tramo o una zona del mismo actor, así que sumar entre elementos
  contaría dos veces.

## Licencia

Cada capa tiene su ítem en ArcGIS Online, del usuario `SecretariaMovilidad`. Los veinte ítems
(búsqueda `owner:SecretariaMovilidad AND title:"2022-2025"`, 2026-11-05) dicen en `licenseInfo`
«Creative Commons Attribution 4.0» y en `accessInformation` «Oficina de Seguridad Vial -
Secretaría Distrital de Movilidad». Evidencia:
`https://www.arcgis.com/sharing/rest/content/items/432677bf93c74af6a1e040570c2b940f?f=json`.

## Lo medido (2026-11-05)

- **Nombres de campo:** cada capa los nombra a su manera (`FALLECIDO_PC_BICI_ART`,
  `FALL_BICI_TC_BICI_ART`, `FALLECIDOS__ZC_PEAT_LOC`…). La copia los junta por los `alias` de la
  ficha.
- **Geometría:** 156 puntos, 130 polígonos, 1 multipolígono y 86 líneas. Los tramos de la red
  arterial son polígonos (la vía con su ancho); los de la no arterial, líneas. El servicio está en
  el wkid 11116; la copia pide EPSG:4326.
- **Longitud de los tramos:** viene en metros en unas capas y en kilómetros en otras, y el alias
  de `LONG_KM_TC_PEAT_LOC` dice «(m)». No se copia, ni las tasas por km, por 100 m o por hectárea
  que salen de ella.
- **Localidad:** solo la red no arterial la trae (110 sitios sin ella), escrita de varias formas
  (BOSA y Bosa; «Rafel Uribe Uribe»). Sale tal cual, como `localidad_en_la_fuente`.
- **Dirección:** las 66 zonas no la traen.
- **Códigos:** `codigo_sdm` (A, PM_1, Zona H…) se repite entre capas. La clave es `id_elemento`.
- **Ítem cruzado:** el ítem 31f6c497df90474ca4f7cfbf823077a6 se llama «Puntos Críticos … Vías
  Locales», pero apunta a `ZonasCriticasVulnerables_Local_2225`. La capa de puntos de vulnerables
  no arteriales existe y se copia de su propio servicio.
- **Canario:** en [-74.16, 4.60, -74.12, 4.64] (Kennedy y Puente Aranda) hay 49 sitios: 17 de
  vulnerables, 14 de motociclistas, 10 de peatones y 8 de ciclistas. Se midió cruzando cada
  geometría de la descarga con el rectángulo, y la copia da lo mismo, en 2 s por el túnel.

## Lo que no trae

- Los siniestros uno por uno: el SIGAT (`Accidentalidad/AccidentalidadAnalisis`) no declara
  licencia y su tabla de actor vial trae fecha de nacimiento, edad y género.
- Los sitios que no llegaron a críticos: que un lugar no salga no quiere decir que no tenga
  siniestros.
- Ocupantes de carro, de bus o de camión por separado.
- El resto del país.
