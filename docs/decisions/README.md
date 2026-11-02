# Decisiones de arquitectura (ADR)

Formato [MADR 4.0](https://adr.github.io/madr/) corto. Una decisión por archivo; se cambia con una ADR nueva que reemplaza a la anterior.

| # | Decisión | Estado |
|---|---|---|
| 0001 | Repo público `terranova` (Apache 2.0 + CC BY-SA para datos); conectores siguen en GEO_COPILOT | **aceptada** |
| 0002 | La puerta es un servicio nuevo que llama a los conectores por MCP en red interna | **aceptada** |
| 0003 | FastMCP 4.1.x fijado en la puerta; conectores en `mcp` 1.28 hasta migrarlos aparte | **aceptada** |
| 0004 | Un núcleo, dos adaptadores (REST y MCP) desde los mismos modelos | **aceptada** |
| 0005 | Contrato `rt/1` con procedencia por fuente, compatible con GeoResult | **aceptada** |
| 0006 | Una herramienta por pregunta, generada del catálogo; perfiles MCP por familia | **aceptada** |
| 0007 | Catálogo como código con compuerta de licencia y lista blanca de campos | **aceptada** (enmendada 2026-11-01: producción solo ve lo vendible) |
| 0008 | En vivo por defecto; copia y curado solo cuando agregan valor; caché con frescura declarada | **aceptada** |
| 0009 | Llaves API por organización ahora; OAuth 2.1 después | **aceptada** |
| 0010 | Créditos como unidad de cuota por llave (Redis) y medición por evento; fallas y caché no descuentan; crédito por tipo de pregunta; 402 al agotar | **aceptada** (enmendada) |
| 0011 | Errores RFC 9457 con código estable, idénticos en REST y MCP | **aceptada** |
| 0012 | La puerta no usa LLM | **aceptada** |
| 0013 | Observabilidad OTel + Prometheus; canarios diarios (Actions y servidor) | **aceptada** |
| 0014 | Datos de personas fuera del MVP; producto aparte si se decide | **aceptada** |
| 0015 | Despliegue en una VM con Docker Compose y Caddy | **aceptada** |
| 0016 | Versión en la URL, cambios aditivos, `Deprecation`/`Sunset` | **aceptada** |
| 0017 | Lotes de 50 y trabajos lentos con `Prefer: wait` → 202 | **aceptada** |
| 0018 | Política de acceso: API/bulk sí, HTML público con cortesía, backend interno solo con permiso escrito (en ningún plan sin él), captcha nunca | **aceptada** |
| 0019 | Licencia por ítem; CC BY-SA como supuesto por defecto | **aceptada** |
| 0020 | Gratuito al inicio: sin cobro, con llave y cuota para proteger las fuentes | reemplazada por 0029 |
| 0021 | Open-Meteo (GloFAS, ERA5) con el API gratis mientras sea gratuito; salida a Copernicus directo | **superada** (ADR-0029; retirada el 2026-10-28) |
| 0022 | Agrología del IGAC en vivo con caché hasta tener copia (licencia por ítem y descarga de capacidad pendientes) | **aceptada** |
| 0029 | Freemium de pago: nivel gratis y planes por saldo mensual que no se acumula; 402 al agotar; el cobro vive fuera de la puerta | **aceptada** |

- [ADR-0001 · Repo público `terranova`](0001-repo-publico-terranova.md)
- [ADR-0002 · La puerta llama a los conectores por MCP en red interna](0002-la-puerta-llama-a-los-conectores-por-mcp-en-red-interna.md)
- [ADR-0003 · Versión del protocolo y librerías](0003-version-del-protocolo-y-librerias.md)
- [ADR-0004 · Un núcleo, dos adaptadores](0004-un-nucleo-dos-adaptadores.md)
- [ADR-0005 · Contrato `rt/1`](0005-contrato-rt-1.md)
- [ADR-0006 · Una herramienta por pregunta, generada del catálogo](0006-una-herramienta-por-pregunta-generada-del-catalogo.md)
- [ADR-0007 · Catálogo como código](0007-catalogo-como-codigo.md)
- [ADR-0008 · En vivo, copia y curado](0008-en-vivo-copia-y-curado.md)
- [ADR-0009 · Identidad](0009-identidad.md)
- [ADR-0010 · Cuotas y medición](0010-cuotas-y-medicion.md)
- [ADR-0011 · Errores](0011-errores.md)
- [ADR-0012 · La puerta no usa LLM](0012-la-puerta-no-usa-llm.md)
- [ADR-0013 · Observabilidad y canarios](0013-observabilidad-y-canarios.md)
- [ADR-0014 · Datos de personas](0014-datos-de-personas.md)
- [ADR-0015 · Despliegue](0015-despliegue.md)
- [ADR-0016 · Versionado](0016-versionado.md)
- [ADR-0017 · Lotes y trabajos lentos (M2)](0017-lotes-y-trabajos-lentos-m2.md)
- [ADR-0018 · Política de acceso a las fuentes](0018-politica-de-acceso-a-las-fuentes.md)
- [ADR-0019 · Licencias por ítem y BY-SA por defecto](0019-licencias-por-item-y-by-sa-por-defecto.md)
- [ADR-0020 · Gratuito al inicio](0020-gratuito-al-inicio.md)
- [ADR-0021 · Open-Meteo mientras Terrnova sea gratuito](0021-open-meteo-mientras-sea-gratuito.md)
- [ADR-0022 · Agrología del IGAC en vivo, con caché, hasta tener copia](0022-agrologia-igac-en-vivo-hasta-tener-copia.md)
- [ADR-0023 · Tope de la ficha en 12 s: el gate F4 no espera la copia de agrología](0023-tope-de-la-ficha-12-s.md)
- [ADR-0024 · Conector de copia (G3): copias en PostGIS servidas por la puerta](0024-conector-de-copia.md)
- [ADR-0025 · El documento de contratistas y proponentes de SECOP se muestra como lo publica la fuente](0025-documentos-en-divulgacion-obligatoria.md)
- [ADR-0026 · Cobertura de datos abiertos: conector genérico + buscador de catálogo (G6), no un tool por dataset](0026-cobertura-datos-abiertos-buscador-no-tool-por-dataset.md)
- [ADR-0027 · CLI de cliente: un cliente delgado del REST /v1, con `catalogo buscar` y `verificar <archivo>`](0027-cli-de-cliente.md)
- [ADR-0028 · Descubrimiento del catálogo con embeddings (buscador semántico), reconciliado con ADR-0012](0028-descubrimiento-con-embeddings.md)
- [ADR-0029 · De gratuito a freemium de pago](0029-de-pago-freemium.md)
- [ADR-0030 · Despliegue en una VPS única con Docker Compose (no nube gestionada) para el arranque](0030-despliegue-vps-unica-compose.md)
- [ADR-0031 · MCP a escala: herramientas tipadas, perfiles por familia y perfil «catálogo» (enmienda la ADR-0006)](0031-mcp-a-escala-perfiles-y-catalogo.md)
- [ADR-0032 · La geometría completa, bajo pedido: por defecto cada polígono va como su envolvente](0032-geometria-completa-bajo-pedido.md)
- [ADR-0033 · Las listas largas salen por páginas de 50; los totales cuentan la lista completa](0033-listas-largas-por-paginas.md)
- [ADR-0034 · Llave de prueba con correo verificado y formulario de contacto propio](0034-alta-con-correo-verificado.md)
- [ADR-0035 · Consulta por polígono en las copias espaciales](0035-consulta-por-poligono.md)
