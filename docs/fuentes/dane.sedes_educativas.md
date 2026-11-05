# DANE: sedes educativas (SISE)

Fuente `dane.sedes_educativas`. Herramientas: `dane_sedes_educativas_en_zona`,
`dane_sedes_educativas_municipio` y `dane_sedes_educativas_buscar`.

## Qué es

El Sistema de Identificación de Sedes Educativas (SISE) del DANE: el punto de cada sede educativa
activa, con su código DANE de 12 dígitos, el mismo de Saber 11 y de los registros del MEN.

- **Servicio:** capa 0 de
  `services.arcgis.com/ioNRSZMYYlx0PUaB/arcgis/rest/services/SedesEducativasSISE/FeatureServer`.
  Es el ítem `eaeee68220a74ce88c65e91320ab0116` del hub cdge.dane.gov.co.
- **Tamaño:** 56 650 sedes, todas con `ESTADO = ACTIVA`.
- **Corte:** el servicio se editó por última vez el 2024-11-14 (integrado al MGN 2024).
- **Copia:** va en una copia espacial (ADR-0024) que se bajó en 52 s. A diferencia del geoportal
  del DANE, este servicio sí responde desde la VPS.

## Licencia

Es la licencia del Geoportal del DANE (ADR-0039), la misma de `dane.cnpv2018.municipio`: CC BY 4.0
para la información georreferenciada que produce el DANE. El ítem del hub no repite la licencia:
se hereda del geoportal.

El MEN publica un corte más nuevo (`DANE_SISE_Pt`, 2025-12, 56 743 sedes), pero su organización
niega la reutilización y la redistribución. No se usa.

## Lo medido (2026-11-05)

- **Puntos repetidos:** 14 658 sedes (26 %) comparten su punto con otra, y 481 de Uribia están en
  un mismo punto. En lo rural, el punto puede ser el de la cabecera o el de la sede principal. Las
  herramientas lo avisan.
- **Zona:** 37 379 rurales y 19 271 urbanas.
- **Sector:** 44 360 oficiales y 12 290 no oficiales.
- **`NATURALEZA`:** es la naturaleza jurídica del prestador (oficial, organización con o sin fines
  de lucro, persona natural, comunidad religiosa, régimen especial). No es lo mismo que el sector.
- **`NIVEL`:** casi siempre trae un nivel; 300 sedes traen varios, separados por comas.
- **Por municipio:** Bogotá tiene 2 595 sedes, Cali 1 046 y Medellín 847. Esas listas siguen por
  páginas (ADR-0040).
- **Contacto:** 6 514 sedes traen correo y 6 112 un celular.
  - Salen como los publica el DANE, y no se busca por ellos.
  - En las doradas del repo van tapados: el repo no versiona contactos que pueden ser de una
    persona.
- **Canarios:**
  - 6 sedes en [-74.07, 4.6, -74.06, 4.61], la misma cifra en el servicio y en la copia;
  - 7 sedes en Cubarral (50223);
  - «Divino Niño Cubarral» da la sede 250223000114.

## Lo que no trae

- Matrícula, docentes y resultados: para los resultados está `icfes_saber11`, que se une por el
  código DANE.
- Sedes cerradas: el servicio solo trae las activas.
