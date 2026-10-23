# Plan de expansión (F5): todas las fuentes objetivo

*2026-10-22.* Cómo pasar de las 20 herramientas de M1 a las ~139 de
[FUENTES_OBJETIVO.md](FUENTES_OBJETIVO.md), que es el gate F5 y la meta de M2. Este plan detalla la
sección F5 del [ROADMAP](ROADMAP.md) y no cambia sus reglas.

## Punto de partida

- **Hecho:** gates F0–F4. La receta para sumar una herramienta ya está probada de punta a punta:
  ficha en el catálogo, prueba dorada, canario con verdad medida, licencia por ítem, `campos` del
  canario, REST y MCP generados y métricas.
- **Herramientas hoy:** 20 de ~139, más la ficha de un lugar.
- **En paralelo:** F6 (GEO Copilot como cliente). La VM espera: todo se valida en el compose local
  y se despliega al final (ADR-0015).
- **En espera:** la ola 6, que necesita permiso escrito (ADR-0018). No se toca hasta tener la
  respuesta.

## Definición de terminado de una herramienta

Una herramienta cuenta como servida cuando cumple todo esto:

0. La fuente tiene **perfil** ([spec 07](specs/07-perfil-de-fuente.md)): qué es una fila, si la clave es única,
   qué trae mal, cómo responde y qué se decide con eso. La herramienta se diseña sobre el perfil.
   Y tiene **ficha técnica** ([spec 08](specs/08-ficha-tecnica.md)) cosechada de la fuente: años que cubre,
   geometría, CRS y capas, diccionario de campos, última actualización y corte.
1. Tiene ficha de fuente y de herramienta en `catalogo/`, y `scripts/validar_catalogo.py` pasa.
2. La licencia está verificada por ítem (ADR-0019). Si no, queda `por_verificar` y solo responde con
   llaves de evaluación (ADR-0007).
3. Tiene prueba dorada grabada en vivo (`scripts/grabar_doradas.py`) y `canario.campos`
   (`scripts/campos_canario.py`).
4. El canario usa una verdad medida en la fuente, nunca copiada de la respuesta de la puerta.
5. Lo que la fuente publica sale como lo publica (ADR-0025): no se tapan ni se alteran campos. La
   lista blanca elige qué campos responden la pregunta. Lo que no se hace (ADR-0014): buscar por
   nombre o cédula, cruzar fuentes para armar el perfil de una persona y versionar datos personales
   en el repo (doradas, fichas técnicas).
6. Su canario pasa **3 días en verde** antes de contarla en el avance.

## Reglas aprendidas de las fuentes

Cada una salió de un caso medido. Se revisan todas al diseñar una herramienta nueva.

| Regla | Caso que la originó |
|---|---|
| Si la clave no es única, no se cuentan ni suman filas: etapa previa por registro (`previo_select`/`previo_group`) o `distinct` | ICFES (estudiantes repetidos), SECOP Integrado (un contrato por estado), PAA de SECOP II (un ítem por categoría UNSPSC) |
| Contar lo que se pregunta, con nombre propio: `count(distinct …)` si una fila no es un caso | SIC: sancionados ≠ resoluciones |
| Un código de la fuente no es una entidad: un NIT puede tener varias | PAA de SECOP II: Pitalito = municipio, concejo y personería |
| Si la fuente está partida (vigente e histórico), cada mitad tiene herramienta y se remiten entre sí. Así «no encontrado» no esconde un «está en la otra mitad» | SECOP I: vigente desde 2018, histórico 2004–2017 |
| Las filas de prueba de la fuente se excluyen en la consulta | multas de SECOP I: «Z ENTIDAD DE PRUEBA» |
| Los valores imposibles o de relleno (1899-12-30, 2099, «No Definido», 0) se dicen en la ficha técnica; no se toman por datos | vigencias del IGAC, fechas de SECOP, NIT de las multas |
| Los códigos llevan la norma que los define; lo que ninguna norma define sale como `sin_definir` | destino económico (U a Z), uso de la construcción (101 a 127) |
| Una fecha de la fuente puede ser futura y valer: se explica en la descripción | TRM de mañana, UVR hasta el 15 del mes siguiente |
| El nombre de una fuente no basta: se verifica qué entrega | «ERA5» de Open-Meteo era una mezcla con IFS |
| En Socrata, ordenar un `distinct` grande no responde: sin orden si cabe en una página | PAA de SECOP II |
| Si contar un mes pasa de 300 s, la fuente no se copia ni se sirve en vivo: sería carga | ofertas de SECOP II |
| El canario de una fuente con personas se elige con personas jurídicas, y una prueba lo vigila | multas de SECOP I (NIT de empresa) |

## Piezas genéricas

Se construyen al inicio, porque la mayoría de las herramientas depende de alguna. Cada una tiene su
spec y su prueba antes de usarla en una ola.

| Pieza | Qué es | Dónde vive | Destraba |
|---|---|---|---|
| **G1 · Agregados en Socrata** | `datos_consultar` con `$group` y conteos, con un **n mínimo** por celda (ICFES: n ≥ 10) | `datos_abiertos_mcp` (GEO Copilot) | ICFES, MinEducación, transacciones, SECOP agregado |
| **G2 · Corte mensual del IGAC** | Descubre el nombre vigente de `Base_Catastral_Publica_del_Gestor_IGAC_<MM>_<AAAA>` y lo deja en el catálogo; el canario avisa del cambio de mes | Terranova (job) + catálogo | las ~13 herramientas catastrales |
| **G3 · Conector de copia** | Bulk o Socrata → PostGIS en `copia.*`, con huella, versión vigente, frescura (TTL de la fuente) y job programado. La puerta sirve `servido_desde: copia` y nunca presenta una copia vencida como actual (ADR-0008). Generaliza el pipeline de F4.1 | Terranova | SECOP (búsquedas y medianas), transacciones, TerriData, anexos DANE, directorio DIAN |
| **G4 · Conector de scrape con estado** | Navega formularios WebForms/JSF (ViewState), con tasa baja, `User-Agent` propio, caché y copia, y registra URL y fecha. Respeta `robots.txt`. **Nunca** captchas, logins ni retos de identidad (ADR-0018) | nuevo `html_mcp` (GEO Copilot) | normas, jurisprudencia, SIPI, Imprenta, ANM |
| **G5 · Herramientas de la fábrica** | `scripts/nueva_fuente.py` (andamio de fichas), medición de «horas por fuente» y el tablero de avance (canario verde / objetivo) | Terranova | todas |

Reglas de las copias en local:

- La memoria del equipo es poca. Las copias grandes (SECOP: 22,8 M filas; transacciones: 30,9 M) se
  construyen **por partes** y solo con las columnas y los años que sirve la herramienta.
- La copia completa se construye en la VM.
- Una copia se baja **una vez** y luego se actualiza por incremento. Nunca se pagina en vivo un
  servicio del Estado para copiarlo entero: eso es carga.

## Olas

El orden va por valor y por facilidad. Dentro de cada ola se avanza fuente por fuente, y cada fuente
cierra con su definición de terminado.

### Ola 1 · Territorio completo y contratación (~35)

| Fuente | Herramientas | Pieza | Esf. |
|---|---|---|---|
| IGAC base catastral: perímetro, sector, nomenclatura vial y domiciliaria, terreno y construcción urbanos y rurales, REGISTRO_1/2 por código predial (sin nombres ni documentos) | ~8 | G2 | S–M |
| IGAC zonas homogéneas (ZHG con valor, ZHF) | 2 | G2 | S |
| IGAC estadísticas municipales y gestores catastrales | 2 | — | S |
| Transacciones inmobiliarias 2015–2023 (conteos y medianas por municipio) | 2 | G1 + G3 | S + M |
| ICFES Saber 11 (agregados) y MinEducación | 4 | G1 | S |
| SECOP I y II: procesos, contratos, adiciones, garantías, ejecución, pagos, modificaciones, oferentes, plan anual, sanciones; búsqueda por texto y por entidad | ~16 | G1 + G3 | S + M |

### Ola 2 · Victorias rápidas (~21)

INVIMA (CUM, registros, dispositivos), directorio DIAN de comercio exterior, sanciones SIC, SUIT,
ANCP-CCE (conceptos y providencias), BanRep (SDMX), UPRA (13 departamentos y la búsqueda de los 5
que faltan), Supersociedades (NIIF y las 10 000 más grandes) y RUES abierto (sin perfiles de
personas: solo por NIT o matrícula).

### Ola 3 · Normas y datos de desarrollo (~21)

Corte Constitucional (índice por API y texto por HTML), gestores normativos (Función Pública, CREG,
Normograma DIAN, Superfinanciera, normativa SIC), anexos DANE (IPM, pobreza, GEIH) y TerriData (copia;
licencia por pedir).

### Ola 4 · Jurisprudencia y ambiente local (~27)

SAMAI, Consejo de Estado, CNDJ, Imprenta Nacional (Diario Oficial y Gaceta del Congreso), ANM. SIATA
queda en espera hasta tener permiso escrito, porque su backend es interno (ADR-0018).

### Ola 5 · Propiedad industrial y Corte Suprema (~13)

SIPI y gaceta de la SIC, WebRelatoria de la Corte Suprema. Son los de mayor esfuerzo (L).

### Ola 6 · Con permiso (~9) · **en espera**

Geovisor IGAC (avalúo por predio), SIIS de Supersociedades, CPNU. Solo con respuesta escrita a los
derechos de petición (F0.8).

## Cómo se mide el avance

- **Herramientas con canario verde 3 días / herramientas objetivo**, por ola.
- **Horas por fuente**, desde «fuente elegida» hasta «canario verde 3 días».
- **Banco de agente** por familia ≥ 90 %: preguntas de las verdades del producto
  (`catalogo/verdades_producto.yaml`) respondidas con LLM real y revisadas una por una.

## Riesgos y cómo se cuidan

| Riesgo | Cuidado |
|---|---|
| Licencia sin verificar | queda `por_verificar` y solo responde en evaluación; nunca sale a producción |
| Datos personales dentro de conjuntos abiertos (proveedores SECOP, RUES, titulares SIC) | lista blanca de campos; sin búsqueda por persona; revisión de cada ficha |
| Carga sobre servidores del Estado | copia con incremento, caché, tasa baja y una sola llamada por canario al día |
| Cambios de esquema y de URL (IGAC cada mes, WebForms) | `canario.campos` (`esquema_cambiado`), G2 para el corte mensual, runbook §2 |
| Memoria del equipo local | copias por partes; una pieza pesada a la vez; el stack se apaga al terminar |

## Inventario de SECOP (46 conjuntos oficiales de Colombia Compra en datos.gov.co)

Revisado el 2026-10-22 con el catálogo de datos.gov.co (atribución «Colombia Compra Eficiente»).
Cada conjunto tiene su herramienta o la razón por la que todavía no.

| Conjunto | Herramienta | Estado |
|---|---|---|
| SECOP II contratos `jbjy-vk9h` | `secop_contrato_por_id`, `secop_contratos_municipio`, `secop_contratos_entidad`, `secop_contratos_buscar` (copia) | ✅ |
| SECOP II procesos `p6dx-8zbt` | `secop_proceso_por_id` | ✅ |
| SECOP integrado `rpmr-utcd` | `secop_integrado_contratos_entidad` | ✅ |
| Proponentes SECOP II `hgi6-6wh3` | `secop_proponentes_proceso` | ✅ |
| Adiciones, garantías, ejecución, plan de pagos, modificaciones, suspensiones, sanciones (SECOP II) | `secop_*_contrato` | ✅ |
| Facturas `ibyt-yi2f`, compromisos `skc9-met7`, rubros `cwhv-7fnp`, CDP `a86w-fh92`, ubicaciones `gra4-pcp2` | `secop_*_contrato` | ✅ |
| Cronograma `f3ev-294c`, BPIN `d9na-abhe` | `secop_cronograma_proceso`, `secop_bpin_proceso` | ✅ |
| SECOP I procesos `f789-7hwg`, adiciones `7fix-nd37`, modificaciones `36vw-pbq2` y `u5b4-ae3s`, origen de los recursos `3xwx-53wt`, proponentes `tauh-5jvn`, archivos `ps88-5e3v` | `secop1_*` | ✅ |
| Convenios interadministrativos `s484-c9k3` | `secop_convenio_interadministrativo` | ✅ |
| Ofertas SECOP II `wi7w-2nvm` y su histórico `b28v-edj8` | — | **no se sirve**: no indexa por proceso ni por fecha (contar un mes pasa de 300 s), así que copiarla sería carga sobre el portal. Quién ofertó lo responde `secop_proponentes_proceso`; el valor de cada oferta espera un bulk de Colombia Compra |
| Archivos de SECOP II por año (`dmgg-8hin`, `h4m3-b4e2`, `nbae-kzan`, `3skv-9na7`, `kgcd-kt7i`, `f8va-cf4m`) | — | 134 M filas por año: copia (G3) por ventana |
| PAA de SECOP I `prdx-nxyp` y `azeg-sgqg` | `secop1_paa_entidad`, `secop1_paa_detalle` | ✅ (el encabezado se agrupa: la fuente lo repite por versión; el NIT viene a veces con dígito de verificación) |
| PAA de SECOP II, detalle `9sue-ezhx` | `secop2_paa_entidad` (por NIT: una fila por entidad del NIT), `secop2_paa_items` (por código de entidad) | ✅ (el detalle trae el NIT; un ítem se repite por categoría UNSPSC: el valor se deduplica por ítem. El encabezado `b6m4-qgqv` queda para el presupuesto general) |
| Proveedores registrados `qmzu-gj57`, grupos de proveedores `ceth-n4bn` | — | **no se sirve**: el campo `nit` trae cédulas (un «ECOPETROL S.A.» registrado con la cédula de una persona) y personas inscritas como sociedades. Una herramienta por NIT daría datos engañosos; RUES (`rues_empresa_por_nit`) cubre la empresa |
| Multas SECOP I `4n4q-k399` | `secop1_multas_municipio` | ✅ (la llave es el municipio: el NIT de la entidad casi siempre dice «No Definido»; 94 filas son de una entidad de prueba y se excluyen) |
| SECOP I procesos histórico `qddk-cgux` | `secop1_proceso_historico_por_constancia` | ✅ (la vigente empieza el 2018-01-01 y el histórico cubre 2004–2017: sin él, una constancia de 2015 daba «no encontrado») |
| Convenios histórico `ityv-bxct` | — | no hace falta: la vigente se recargó entera en 2023 y trae firmas desde 2000 |
| SECOP I archivos histórico `8kpz-m6cc`, modificaciones a procesos SECOP II `e2u2-swiw` (sin actualizar desde 2021) | — | después: mismos esquemas que los vigentes |
| Contactos de entidades y proveedores `4ex9-j3n8`, ubicaciones adicionales `wwhe-4sq8` | — | fuera: son contactos y direcciones (ADR-0014) |
