# Decisiones de arquitectura (ADR)

Formato [MADR 4.0](https://adr.github.io/madr/) corto. Una decisión por archivo; se cambia con una ADR nueva que reemplaza a la anterior.

| # | Decisión | Estado |
|---|---|---|
| 0001 | Repo público `terranova` (Apache 2.0 + CC BY-SA para datos); conectores siguen en GEO_COPILOT | **aceptada** |
| 0002 | La puerta es un servicio nuevo que llama a los conectores por MCP en red interna | propuesta |
| 0003 | FastMCP 4.1.x fijado en la puerta; conectores en `mcp` 1.28 hasta migrarlos aparte | propuesta (spike F0) |
| 0004 | Un núcleo, dos adaptadores (REST y MCP) desde los mismos modelos | propuesta |
| 0005 | Contrato `rt/1` con procedencia por fuente, compatible con GeoResult | propuesta |
| 0006 | Una herramienta por pregunta, generada del catálogo; perfiles MCP por familia | propuesta |
| 0007 | Catálogo como código con compuerta de licencia y lista blanca de campos | propuesta |
| 0008 | En vivo por defecto; copia y curado solo cuando agregan valor; caché con frescura declarada | propuesta |
| 0009 | Llaves API por organización ahora; OAuth 2.1 después | propuesta |
| 0010 | Créditos como unidad de cuota por llave (Redis) y medición por evento; fallas y caché no descuentan | propuesta |
| 0011 | Errores RFC 9457 con código estable, idénticos en REST y MCP | propuesta |
| 0012 | La puerta no usa LLM | propuesta |
| 0013 | Observabilidad OTel + Prometheus; canarios en el servidor | propuesta |
| 0014 | Datos de personas fuera del MVP; producto aparte si se decide | propuesta |
| 0015 | Despliegue en una VM con Docker Compose y Caddy | propuesta |
| 0016 | Versión en la URL, cambios aditivos, `Deprecation`/`Sunset` | propuesta |
| 0017 | Lotes de 50 y trabajos lentos con `Prefer: wait` → 202 | propuesta (M2) |
| 0018 | Política de acceso: API/bulk sí, HTML público con cortesía, backend interno solo con permiso, captcha nunca | propuesta |
| 0019 | Licencia por ítem; CC BY-SA como supuesto por defecto | propuesta |
| 0020 | Gratuito al inicio: sin cobro, con llave y cuota para proteger las fuentes | **aceptada** |

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
