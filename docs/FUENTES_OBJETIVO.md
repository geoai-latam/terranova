# Fuentes objetivo (Colombia)

Lista de las fuentes oficiales abiertas que Terrnova debe servir para M2. Todos los puntos de acceso
se consultaron el 2026-10-21. «Verificado» quiere decir que se llamó al punto de acceso y devolvió
datos.

**Meta:** unas **139 herramientas** sobre fuentes abiertas, más las propias de territorio (cruces,
ficha, amenazas, imágenes) que ya existen en los conectores de
[GEO Copilot](https://github.com/geoai-latam/geo-copilot).

Convenciones:

- **Acceso** (según [ADR-0018](decisions/0018-politica-de-acceso-a-las-fuentes.md)):
  - API: REST o SoQL abiertos.
  - Bulk: archivo descargable.
  - HTML: página pública sin captcha.
  - Interno: backend de la aplicación web de la entidad. Solo se usa con permiso escrito.
- **Esfuerzo:** S < 1 día · M 1–3 días · L > 3 días.
- **Licencia:** todos los conjuntos de datos.gov.co revisados son **CC BY-SA 4.0**. Los ítems de la
  base catastral IGAC en ArcGIS Online también. Normas y sentencias se pueden reproducir libremente si
  la copia es fiel (Ley 23 de 1982, art. 41). La licencia se registra **por ítem**
  ([ADR-0019](decisions/0019-licencias-por-item-y-by-sa-por-defecto.md)).

## Resumen por familia

| Familia | Herramientas aprox. | Acceso dominante | Notas |
|---|---|---|---|
| Territorio: IGAC catastro, transacciones, UPRA, DANE, TerriData | ~30 | API + bulk | la base IGAC cambia de nombre cada mes |
| Ambiente local: SIATA (Valle de Aburrá), ANM | ~13 | interno + HTML/PDF | licencia SIATA por pedir |
| Educación y economía: ICFES, MinEducación, BanRep | ~7 | API | ICFES solo agregados con n mínimo |
| Contratación: SECOP I y II | ~16 | API + copia nocturna | 22,8 M filas; sin perfiles de personas |
| Empresas: RUES abierto, Supersociedades NIIF | ~9 | API | SIIS y relatoría solo con permiso |
| SIC: sanciones, propiedad industrial, normativa, actos, gaceta | ~18 | API + HTML con estado | titulares con datos personales |
| Regulación y normas: SFC, CREG, Función Pública, Imprenta, SUIT, trámites | ~16 | HTML + API | |
| INVIMA y DIAN (doctrina, directorio de comercio exterior) | ~8 | API + bulk + HTML | la validación de CUFE tiene captcha: fuera |
| Jurisprudencia: Constitucional, Suprema, Consejo de Estado, SAMAI, CNDJ, ANCP-CCE | ~15 | HTML + API | |
| Procesos por número: Rama Judicial (radicado), SPOA, quejas SFC, SIMEV | ~6 | API / HTML | nunca búsqueda por persona |

## Puntos de acceso verificados

### Territorio

- **IGAC base catastral pública mensual** (ArcGIS Online, org IGAC_OIT):
  `https://services2.arcgis.com/RVvWzU3lgJISqdke/arcgis/rest/services/Base_Catastral_Publica_del_Gestor_IGAC_<MM>_<AAAA>/FeatureServer`
  - Capas urbanas: 0 nomenclatura vial · 1 domiciliaria · 2 perímetro · 3 construcción · 5 manzana
    (171 814) · 7 terreno · 8 sector.
  - Capas rurales: 9–16, entre ellas la 15 R_VEREDA (17 678).
  - Tablas: 17 REGISTRO_1 (6 812 177) y 18 REGISTRO_2 (7 351 847).
  - **No trae nombres ni documentos.** CC BY-SA 4.0. Esfuerzo S–M.
- **IGAC zonas homogéneas:** `Zonas_Homogeneas_Gestor_IGAC_Vigencias_2026/FeatureServer`.
  - ZHG con valor por m² o por ha: capas 11 y 13.
  - ZHF: capas 15 y 16.
  - Esfuerzo S.
- **IGAC estadísticas municipales:** `Municipios_Estadisticas/FeatureServer/0` (123 325), con avalúo
  total, predios, vigencias y estado catastral. Esfuerzo S.
- **IGAC gestores catastrales:** datos.gov.co `bhcx-bx97`. Esfuerzo S.
- **IGAC avalúo por predio:** backend del Geovisor `POST servicioscem.igac.gov.co/Geovisor/catastral`.
  Es **interno: solo con permiso**. Esfuerzo M.
- **Transacciones inmobiliarias 2015–2023:** datos.gov.co `7y2j-43cv` (30,9 M). La mediana necesita
  copia. Esfuerzo S + M.
- **UPRA precios de tierra rural:** datos.gov.co `rttb-pk7n` (13 departamentos; faltan 5, que quizá
  estén en SIPRA). Esfuerzo S + M.
- **DANE:**
  - CNPV 2018 por municipio: geoportal `Serv_DatosCNPV2018_Integrados_MGN2018/MapServer/800`.
  - Anexos xlsx: IPM municipal 2018, pobreza 2025, GEIH mensual (el nombre cambia).
  - Esfuerzo S + M.
- **TerriData:** bulk `terridata.dnp.gov.co/assets/docs/txt/dimensiones/TerriData.txt.zip` (191 MB).
  Va en copia. Licencia por pedir. Esfuerzo M.
- **SIATA:** `geoportal.siata.gov.co/fastgeoapi/` (temperatura, lluvia, niveles, PM2.5, cámaras,
  alertas). Es **interno: con permiso**. Esfuerzo M.
- **ANM notificaciones:** `anm.gov.co/notificaciones` (HTML + PDF). Sin búsqueda por nombre.
  Esfuerzo L.

### Educación y economía

- **ICFES Saber 11:** `kgxf-xxbe` (7,1 M filas). Solo agregados, con n ≥ 10. Hace falta `$group` en
  el conector Socrata. Esfuerzo S.
- **MinEducación:** `nudc-7mev`, `ji8i-4anb`, `sras-4t5p`. Esfuerzo S.
- **BanRep series:** SDMX oficial `totoro.banrep.gov.co/nsi-jax-ws/rest/…`. Aviso legal: reproducción
  libre sin alterar, citando la fuente y la fecha. Esfuerzo S–M.
- **BanRep repositorio:** DSpace/OAI-PMH, detrás de un muro anti-bots. Los derechos van por ítem.
  Esfuerzo M–L.

### Contratación (datos.gov.co, CC BY-SA, diario)

| Tema | Conjuntos |
|---|---|
| procesos | SECOP II `p6dx-8zbt` · SECOP I `f789-7hwg` · histórico `qddk-cgux` |
| contratos | SECOP II `jbjy-vk9h` · integrado `rpmr-utcd` |
| detalle del contrato | adiciones `cb9c-h8sn` · garantías `gjp9-cutm` · ejecución `mfmm-jqmq` · pagos `uymx-8p3j` |
| modificaciones | `u8cx-r425` · `7fix-nd37` · suspensiones `u99c-7mfm` |
| oferentes y adjudicaciones | `hgi6-6wh3` · ofertas `wi7w-2nvm` · `tauh-5jvn` |
| plan anual | `b6m4-qgqv` + `9sue-ezhx` · SECOP I `prdx-nxyp` + `azeg-sgqg` |
| proveedores | `qmzu-gj57` (**no exponer teléfonos ni correos**) |
| sanciones | `4n4q-k399` · `it5q-hg94` |

### Empresas

- **RUES:** Confecámaras `c82u-588k` (9,4 M) y establecimientos `nb3d-v3n7`. Incluye comerciantes
  que son personas. Esfuerzo S.
- **Supersociedades:**
  - NIIF: `pfdp-zks5`, `prwj-nzxa`, `ctcp-462n`, `y3gh-x5g7`, `6hqw-m3dm`. Hay que pivotear el
    formato XBRL. Esfuerzo M.
  - 10 000 más grandes: `6cat-2gcs`. Esfuerzo S.
  - SIIS (accionistas, revelaciones, insolvencia) y relatoría: **interno, solo con permiso**.
  - Baranda Virtual: captcha, **fuera**.

### SIC

- **Sanciones:** `73dx-n59j`. Esfuerzo S.
- **Propiedad industrial:** SIPI (ASP.NET WebForms). Esfuerzo L.
- **Gaceta:** Excel dentro de SIPI. Esfuerzo M.
- **Normativa y Boletín Jurídico:** HTML. Esfuerzo M.
- **Actos (relatoría):** SPA interna. Esfuerzo M.
- **Trámites:** piden el documento de la parte. **Fuera.**

### Regulación, normas, gacetas y trámites

| Fuente | Acceso | Esf. |
|---|---|---|
| Superfinanciera: normativa por año, doctrina | HTML + PDF | M–L |
| CREG: gestor normativo «Alejandría 2.0» | HTML | M |
| Función Pública: gestor normativo (`norma.php?i=`) | HTML | M |
| Imprenta Nacional: Diario Oficial y Gaceta del Congreso (JSF + PDF) | HTML | M–L |
| SUIT: `k7xp-z2d2` (77 890), `48fq-mxnm`, `dd24-8p6w` | API | S |
| Páginas de trámites de las entidades | HTML | M |

### INVIMA y DIAN

- **INVIMA CUM:** `i7cb-raxc`, `vwwf-4ftk`, `spzp-dfuc`, `vgr4-gemg`. Esfuerzo S.
- **INVIMA registros:** `ui32-p9f2`; dispositivos `y4qt-w6tk`. Esfuerzo S–M.
- **DIAN Normograma:** HTML estático. Esfuerzo M.
- **DIAN directorio de importadores y exportadores:** zip anual (la DIAN ya anonimiza a las
  personas). Esfuerzo S.

### Jurisprudencia

| Fuente | Acceso | Esf. |
|---|---|---|
| Corte Constitucional: índice `v2k4-2t8s` (29 513) + HTML de relatoría | API + HTML | M |
| Corte Suprema: WebRelatoria (JSF) | HTML | L |
| Consejo de Estado: buscador tradicional | HTML | L |
| SAMAI: providencias tituladas y procesos (WebForms) | HTML | M–L |
| CNDJ: relatoria.cndj.gov.co | HTML | M |
| ANCP-CCE: WordPress REST `relatoria.colombiacompra.gov.co/wp-json/wp/v2/conceptos` (7 684) y `/providencias` | API | S |

### Procesos por número (sin búsqueda por persona)

- **Rama Judicial (CPNU) por radicado, lote y directorio de despachos:** la API es pública pero no
  está documentada, así que se pide confirmación al CSJ.
- **SPOA de la Fiscalía:** por número de noticia criminal.
- **Quejas de la SFC:** por radicado.
- **SIMEV:** accionistas de emisores, con cédulas enmascaradas.

## Lo que no entra

- Consultas de personas por cédula o nombre: antecedentes, afiliación en salud, Sisbén, RUNT por
  persona, registro civil.
- Formularios con captcha o reto de identidad.
- Conectores que piden credenciales del usuario (DIAN, bancos).
- Backends de terceros.

Ver [ADR-0014](decisions/0014-datos-de-personas.md) y
[specs/06-seguridad-y-datos.md](specs/06-seguridad-y-datos.md).

## Olas de construcción (F5)

| Ola | Qué | Herramientas |
|---|---|---|
| 1 | IGAC base catastral + ZH + estadísticas (job del corte mensual); `$group` en Socrata → ICFES, MinEducación, transacciones; SECOP con copia nocturna | ~35 |
| 2 | INVIMA, directorio DIAN, sanciones SIC, SUIT, ANCP-CCE, BanRep SDMX, UPRA, NIIF Supersociedades, RUES abierto | ~21 |
| 3 | Corte Constitucional; gestores normativos (Función Pública, CREG, DIAN, SFC, SIC); anexos DANE; TerriData | ~21 |
| 4 | SAMAI, Consejo de Estado, CNDJ, Imprenta, SIATA, ANM | ~27 |
| 5 | SIPI y gaceta de la SIC, Corte Suprema | ~13 |
| 6 | Con permiso: Geovisor IGAC (avalúo), SIIS, CPNU | ~9 |

## Solicitudes por derecho de petición (F0.8)

No son contratos. Son preguntas formales (art. 23 de la Constitución, Ley 1755 de 2015) para tener la
respuesta por escrito:

1. **IGAC:** uso del backend del Geovisor; licencia de la base catastral pública (BY o BY-SA).
2. **Supersociedades:** acceso al SIIS y a la relatoría.
3. **Consejo Superior de la Judicatura:** uso automatizado de la consulta de procesos (CPNU).
4. **AMVA / SIATA:** licencia de los datos del geoportal.
5. **DNP:** licencia de TerriData.
6. **BanRep:** uso del backend de series (o quedarse con el SDMX).

## Candidatos adicionales (descubiertos con G6, 2026-10-25)

Hallados con `catalogo_buscar` / la Discovery API de datos.gov.co; **candidatos de promoción** (ADR-0026,
[spec 09](specs/09-descubrimiento.md)), fuera de las olas actuales. Todos CC BY salvo nota. Antes de
promover: licencia verificada por ítem (ADR-0019) y lista blanca sin datos de personas (ADR-0014).

| Candidato | Entidad | Qué aporta | Salvedad |
|---|---|---|---|
| Actos registrales y escrituras públicas | **SNR** (Superintendencia de Notariado y Registro) | la fuente **autoritativa** del registro (actos de naturaleza jurídica registral, escrituras, títulos), vs el espejo de IGAC que ya servimos | el certificado de tradición en vivo (VUR) está **fuera** (ADR-0018: login/captcha/pago); los actos traen nombres de propietarios → lista blanca |
| Licencias ambientales | **ANLA** | expedientes y licencias ambientales = **restricción de un lugar** (36 datasets) | verificar cuáles son datos geográficos reales vs «activos de información» (inventario de transparencia) |
| Restitución de tierras (estadísticas) | **URT** | solicitudes y demandas de restitución = **riesgo territorial** (contexto) | el micro-dato por predio es **sensible y no abierto**; solo el agregado por municipio/departamento |
| Gestión del riesgo de desastres | **UNGRD** | emergencias y riesgo de desastres = contexto de **amenaza** | muchos registros son inventario; elegir los datasets de datos reales |
| Catastro de los gestores descentralizados | **UAECD (Bogotá)**, catastros de Antioquia, etc. | cubren lo que **IGAC no** (Bogotá no es catastro IGAC) | licencia **por verificar** (varios sin licencia declarada) |

**No es candidato de Socrata:** la **deforestación / alertas de bosque** (clave para EUDR) no está en
datos.gov.co; viene de los geoservicios de IDEAM/SMByC y del GFC2020 de la UE — va como capa ráster/ArcGIS
(ya en el plan), no por este catálogo.

## Candidatos por geovisor / ArcGIS REST (entidades nacionales, 2026-10-25)

Muchas entidades publican **geovisores** que, por debajo, son servidores **ArcGIS REST** (`MapServer` /
`FeatureServer`) — el mismo protocolo que ya consumimos de IGAC, ANT, PNN, UPRA y DANE con el conector
`arcgis_rest`. Son el **segundo camino de descubrimiento**, paralelo a G6: donde datos.gov.co es el
catálogo DCAT de Socrata (tablas), el geoportal es el catálogo de **capas**. Y ese catálogo de capas
**existe y es DCAT**: el **Hub de datos abiertos de la ICDE** (`datos.icde.gov.co`) expone un feed
**DCAT-US 1.1** — la «G6 para geoportales» ya es cosechable, no hipotética (ver abajo). Mismas reglas:
licencia por ítem (ADR-0019, BY-SA si no se sabe), sin datos de personas (ADR-0014), nunca login ni
captcha (ADR-0018), y **una sola llamada de metadatos** por servidor para verificar (nunca carga, como
el canario).

| Candidato | Entidad | Qué aporta | Estado (medido) |
|---|---|---|---|
| **DANE — geoportal completo** | DANE | hoy solo usamos CNPV2018 por municipio; el mismo servidor trae **Divipola**, **MGN** histórico (1993–2025), **veredas**, y decenas de capas de indicadores por tema | **en vivo** (`geoportal.dane.gov.co/mparcgis`): ~90 carpetas; **cola larga** dentro de una fuente ya catalogada |
| **Mapa de Tierras (hidrocarburos)** | **ANH** | bloques y contratos de hidrocarburos = **actividad/restricción de un lugar** (relevante para debida diligencia) | **en vivo** (`geovisor.anh.gov.co`, ArcGIS Server 11.1, 12 servicios); licencia por verificar |
| **Catastro minero** | **ANM** | títulos y solicitudes mineras = restricción de un lugar | ya previsto en **ola 4**; confirmar endpoint ArcGIS vs. descarga |
| **Concesiones e infraestructura** | **ANI**, **INVÍAS** | vías 4G, férreo, puertos, red vial nacional = contexto territorial | geoportal existe; **endpoint ArcGIS por verificar** (las URLs probadas no respondieron) |
| **Páramos y ecosistemas** | **Minambiente / SIAC**, IDEAM | delimitación de páramos, ecosistemas, amenazas = restricción ambiental | **ojo al protocolo:** IDEAM/SIAC publican sobre todo **GeoServer (WMS/WFS)**, no ArcGIS REST → otro conector |

**Fuera por licencia:** el **SGC** (Servicio Geológico Colombiano — geología, amenaza sísmica) tiene
geoservicios ricos, pero su licencia es **restrictiva** (igual que sus capas OGC, ya descartadas en
`CLAUDE.md`): no entra al catálogo sin permiso escrito.

**Honestidad de estado:** «en vivo» = verificado hoy con una llamada de metadatos; «por verificar» = la
entidad tiene geovisor pero no confirmé el endpoint ArcGIS (no se golpea el servidor a ciegas). Ninguno
entra a producción sin su licencia verificada por ítem.

### El catálogo DCAT de capas: el Hub de la ICDE (`datos.icde.gov.co`)

El **centro autoritativo** nacional de datos espaciales abiertos. Es un **ArcGIS Hub** que expone un feed
**DCAT-US 1.1** (`/api/feed/dcat-us/1.1.json`) — el análogo ArcGIS del DCAT de Socrata. Ya lo ingiere G6
(`de_dcat_us`, `terranova catalogo-dcat ingerir --fuente icde`); un solo buscador cubre los dos catálogos
(tablas de Socrata + capas de ArcGIS). Medido el 2026-10-25 (una cosecha del feed):

- **≥10.000 datasets** (el feed topa en 10.000, como el offset de Socrata; el total real es mayor y haría
  falta paginar `/api/search/v1` para la pasada completa).
- **100 % con licencia declarada CC BY 4.0** (vs. 36 % en datos.gov.co). Es un *default* del Hub: sigue
  siendo **declarada**, se verifica al promover (ADR-0019).
- **~99 % IGAC** (9.961/10.000), + PNN (RUNAP, que ya servimos) y UPIT (transporte). `theme` es inútil
  (todo `geospatial`); la entidad no discrimina.
- **Lo que de verdad decide:** la **clase**. ~**8.898 son restitución cartográfica** del IGAC (mapa base
  troceado por plancha: drenajes, construcciones, puentes, cercas, muros, piscinas, tapas, curvas de
  nivel…) y solo ~**1.102 son «Dato temático»** (hidrografía 500k, límites, MDT, ortofoto). `de_dcat_us`
  marca esa clase (`_clase_icde`) para que la promoción se centre en el resto, no en las 9k primitivas.
- **8.701** traen endpoint **ArcGIS REST** directo (consumible por el conector `arcgis_rest`).

**Qué nos aporta (honesto):** su valor es el **inventario/descubribilidad** (un DCAT que lista las capas
del IGAC con su REST y su licencia) y un **puñado de capas temáticas** (hidrografía, MDT, ortofoto), **no
cobertura de entidades nuevas** — es casi todo el mapa base del IGAC, al que ya llegamos por su ArcGIS.
Un *crawl* ciego inundaría el catálogo con 9k primitivas; por eso se ingiere con la clase y se promueve
selectivo.

**Más amplio, por confirmar:** **Colombia en Mapas** (`colombiaenmapas.gov.co`, +8.800 metadatos
multi-entidad) y el **GeoNetwork del IGAC** (`metadatos.igac.gov.co/geonetwork`, **CSW / ISO 19139**) son
el catálogo multi-entidad de verdad, pero por **CSW** (no DCAT-US) y más pesado; `metadatos.igac` **no
respondió** el 2026-10-25 (HTTP 000). Queda como pieza futura si se confirma su endpoint y su licencia.
