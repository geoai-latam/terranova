# Bogotá: equipamientos de emergencia

Fuente `bogota.equipamientos_emergencia`. Herramienta: `bogota_emergencias_en_zona`.

## Qué es

Cuatro capas de la IDE de Bogotá, juntas en una copia espacial con una columna `tipo`:

| Tipo | Entidad | Capa | Filas |
|---|---|---|---|
| estación de bomberos | UAECOB | `serviciosgis.catastrobogota.gov.co/…/emergencias/bomberos/MapServer/0` | 19 |
| estación de policía | Secretaría de Seguridad (SDSCJ) | `oaiee.scj.gov.co/…/EquipamientoPMSDSCJ/MapServer/23` | 21 |
| CAI | Secretaría de Seguridad (SDSCJ) | `oaiee.scj.gov.co/…/EquipamientoPMSDSCJ/MapServer/22` | 158 |
| sede de la red pública de salud | Secretaría de Salud | `serviciosgis.catastrobogota.gov.co/…/salud/instituciones/MapServer/1` | 117 |

No hay una capa pública nacional de estaciones de bomberos ni de policía: la DNBC y la Policía
Nacional no publican esa geografía. Los hospitales del país están en `minsalud_sedes_salud_*`.

- **Copia:** se baja a mano desde Colombia, porque la VPS no llega a los servidores del Distrito.
- **Rutas de otro servidor:** la policía vive en otro servidor (`oaiee.scj.gov.co`). Por eso su
  ruta va completa en `copia.servicios`, que ahora acepta rutas `https://…`.

## Licencia

Cada paquete del portal datosabiertos.bogota.gov.co tiene su licencia (verificadas el
2026-11-05):

- `estacion-de-bomberos-para-bogota`: CC BY 4.0.
- `red-adscrita-de-salud-para-bogota`: CC BY 4.0.
- `estacion-de-policia-para-bogota-d-c`: CC BY-SA 4.0.
- `centro-de-atencion-accion-para-bogota-d-c`: CC BY-SA 4.0. Es el paquete que apunta a la capa
  22, la de los CAI.

La copia junta las cuatro, así que manda la más restrictiva: BY-SA.

## Lo medido (2026-11-05)

- **Nombre de la policía:** `EPONOMBRE` trae la «í» rota en la fuente. `EPODESCRIP` trae el
  mismo nombre bien escrito, y es el que se usa.
- **CAI sin descripción:** los CAI no traen `CAIDESCRIP`. El nombre es `CAINOMBRE`.
- **Id de la capa de bomberos:** la capa no declara `objectIdField` y su id es `OBJECTID_1`. La
  copia toma ahora el campo de tipo OID.
- **Punto vacío:** la sede «Unidad de Servicios de Salud 65 Dindalito» viene con un punto vacío.
  - La fila se copia sin geometría: sale en la tabla, pero no en una zona.
  - Antes, un punto vacío tumbaba la copia.
- **Correos:** el de los CAI es el de la estación y el de salud es el de la subred. No se
  copian.
- **Teléfonos:** son los institucionales; la policía publica un celular por CAI.
- **Canario:** 16 sedes en [-74.09, 4.6, -74.06, 4.63]:
  - 10 CAI;
  - 3 estaciones de policía;
  - 2 sedes de salud;
  - la Estación de Bomberos Central.

## Lo que no trae

- Comandos, URI, cárceles y casas de justicia: son otras capas del mismo servicio.
- IPS privadas: están en `minsalud_sedes_salud_*`.
- El resto del país.
