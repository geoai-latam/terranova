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

1. Tiene ficha de fuente y de herramienta en `catalogo/`, y `scripts/validar_catalogo.py` pasa.
2. La licencia está verificada por ítem (ADR-0019). Si no, queda `por_verificar` y solo responde con
   llaves de evaluación (ADR-0007).
3. Tiene prueba dorada grabada en vivo (`scripts/grabar_doradas.py`) y `canario.campos`
   (`scripts/campos_canario.py`).
4. El canario usa una verdad medida en la fuente, nunca copiada de la respuesta de la puerta.
5. Cumple la lista blanca de campos y no expone personas (ADR-0014): ni teléfonos, ni correos, ni
   búsquedas por nombre o cédula.
6. Su canario pasa **3 días en verde** antes de contarla en el avance.

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
