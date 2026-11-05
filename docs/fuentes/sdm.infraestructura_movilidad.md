# Bogotá: red semafórica, cámaras salvavidas y cicloparqueaderos (SDM)

Fuente `sdm.infraestructura_movilidad`. Herramienta: `sdm_movilidad_en_zona`.

## Qué es

Tres capas de puntos del folder `DatosAbiertos` de `sig.simur.gov.co/arcgis/rest/services`, de la
Secretaría Distrital de Movilidad (SDM), juntas en una copia espacial (ADR-0024) con una columna
`tipo`:

| Tipo | Capa | Filas (2026-11-05) |
|---|---|---|
| semáforo | `RedSemaforica/FeatureServer/0` | 1 747 |
| cámara salvavidas | `CamarasSalvavidas/FeatureServer/0` | 128 |
| cicloparqueadero | `Cicloparqueadero/FeatureServer/0` | 2 203 |

- **Copia:** se baja a mano desde Colombia, porque la VPS no llega a `sig.simur.gov.co`. Las tres
  capas se bajaron en una pasada, una petición a la vez.
- **Columnas:** cada capa trae las suyas. La copia junta la dirección y la fecha de instalación
  por `alias`; las demás quedan vacías en los otros tipos.

## Licencia

Cada capa tiene su ítem en ArcGIS Online, del usuario `SecretariaMovilidad` (leídos el
2026-11-05):

- Red Semafórica, `fccbfaa242374764a1fb8f746573cfad`: «Creative Commons Attribution 4.0», con
  enlace a la licencia.
- Cámaras Salvavidas, `f717f1f43b0c4f37bf5ab519f24fdb85`: «Creative Commons Attribution 4.0», con
  enlace a la licencia.
- Cicloparqueadero, `11168d50f8d54939a8a4a36402cb5277`: «C.C. BY 4.0».

Los tres dicen en `accessInformation` «Secretaría Distrital de Movilidad».

## Lo medido (2026-11-05)

- **Cámaras desmontadas:** 53 de las 128 cámaras dicen «Desmontada - novedad», 67 «Instalada» y 8
  no dicen. La capa trae también las que ya no operan, y el aviso lo recuerda.
- **Localidad:** los semáforos la traen como nombre en mayúsculas y sin tilde (KENNEDY). Las
  cámaras la traen como código del dominio de su capa (01 a 20, 00 «No Aplica») y los
  cicloparqueaderos, con otro dominio (1 a 20, sin el cero). `localidad_significado` sale de esos
  dominios; en los semáforos queda vacío.
- **Dominios publicados:** sector y tipo de usuario (PR, PU), tipología (1 a 8) y sello de
  calidad (1 Oro, 2 Plata, 3 No presenta) del cicloparqueadero se traducen con el dominio de la
  capa.
- **Sin significado publicado:** el funcionamiento del semáforo (BT-TF, CA-TA, RP-TF…) y las
  infracciones de la cámara (C14, C29, C35, D02…) no traen dominio en el servicio. Salen tal
  cual.
- **Vacíos:** 49 cicloparqueaderos tienen la dirección en blanco.
- **Proyección:** las tres capas están en EPSG:4686 con `maxRecordCount` 2000. La copia pide
  EPSG:4326.
- **Canario:** en [-74.07, 4.64, -74.05, 4.66] (Chapinero y Teusaquillo) hay 97 semáforos, 62
  cicloparqueaderos con 1 712 cupos y 5 cámaras (3 desmontadas y 2 instaladas). Se midió cruzando
  cada punto de la descarga con el rectángulo, y la copia da lo mismo, en 2,3 s por el túnel.

## Lo que no trae

- Los comparendos y las infracciones registradas por cada cámara.
- El estado de cada semáforo en tiempo real.
- Las otras capas del folder: barrios vitales, centros locales de movilidad, resaltos parabólicos
  y zonas de cargue y descargue.
- El resto del país.
