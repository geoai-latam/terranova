# Terranova

**Respuestas verificables sobre un lugar de Colombia, desde las fuentes oficiales abiertas, por MCP y
REST, con la fuente y la licencia en cada respuesta.**

> Estado: **diseño (F0)**. Aún no hay código. Lo que existe son las decisiones, las especificaciones
> y la hoja de ruta. Ver [docs/ESTADO.md](docs/ESTADO.md).

## Qué es

Una puerta única (una llave, una cuota, un contrato de respuesta) sobre fuentes oficiales: IGAC,
datos.gov.co/SECOP, DANE, PNN, SIC, Supersociedades, cortes, BanRep, Copernicus, USGS, NASA y más.

- **MCP** para agentes de IA (Claude, ChatGPT, Cursor, cualquier cliente MCP).
- **REST `/v1` con OpenAPI 3.1** para sistemas, scripts y SIG.
- Cada respuesta dice **qué entidad respondió, con qué licencia, cuándo, si está completa
  (`vistos/total`) y desde dónde se sirvió** (fuente, copia, curado, caché u obsoleto).
- **Territorio de primera clase:** predio en un punto, cruces espaciales, ficha de un lugar,
  restricciones, amenazas e imágenes.
- **Gratuito por ahora** (ADR-0020). El repo es privado: Terranova es un producto comercial (enmienda de la ADR-0001).

## Principios

1. Fuente competente: responde la entidad que tiene la competencia sobre el dato.
2. En vivo por defecto; copia o dataset curado solo cuando agrega valor, y siempre declarado.
3. Un solo contrato de respuesta para todas las fuentes y las dos puertas.
4. «No encontrado» es una respuesta; «no se pudo» es un error con código. Nunca un dato inventado ni
   uno viejo disfrazado de actual.
5. Sin LLM en la puerta: determinista y reproducible.
6. Licencia y atribución en cada respuesta; sin perfiles de personas.
7. Solo canales publicados: nunca captchas, logins ajenos ni backends sin permiso.

## Documentos

| Documento | Qué tiene |
|---|---|
| [docs/ESTADO.md](docs/ESTADO.md) | dónde estamos y el siguiente paso |
| [docs/CLIENTES.md](docs/CLIENTES.md) | guía para clientes: llave, primera consulta, MCP, créditos, errores |
| [docs/SLA.md](docs/SLA.md) | borrador del acuerdo de nivel de servicio |
| [docs/ROADMAP.md](docs/ROADMAP.md) | fases F0–F7, cada spec con su aceptación, gates, definición de terminado |
| [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) | diagrama y división del trabajo |
| [docs/decisions/](docs/decisions/README.md) | 20 ADR (MADR) |
| [docs/specs/01-contrato-rt1.md](docs/specs/01-contrato-rt1.md) | el sobre `rt/1`, invariantes y códigos de error |
| [docs/specs/02-catalogo.md](docs/specs/02-catalogo.md) | catálogo como código: fuente y herramienta |
| [docs/specs/03-superficie.md](docs/specs/03-superficie.md) | rutas REST, MCP, ficha de un lugar |
| [docs/specs/04-pruebas.md](docs/specs/04-pruebas.md) | pirámide de pruebas, E2E-01..14, banco de agente |
| [docs/specs/05-metricas-slo.md](docs/specs/05-metricas-slo.md) | SLI, SLO y métricas |
| [docs/specs/06-seguridad-y-datos.md](docs/specs/06-seguridad-y-datos.md) | OWASP MCP, licencias, datos de personas |
| [docs/FUENTES_OBJETIVO.md](docs/FUENTES_OBJETIVO.md) | ~139 herramientas objetivo con puntos de acceso verificados |

## Relación con GEO Copilot

Los conectores (12 servidores MCP: ArcGIS, OGC, datos abiertos, DANE, imágenes, amenazas, rutas…)
viven en [geoai-latam/geo-copilot](https://github.com/geoai-latam/geo-copilot). Terranova es la
puerta, el catálogo y la operación encima de ellos. GEO Copilot es su primer cliente.

## Licencia

Propietaria: © 2026 GeoAI LATAM, todos los derechos reservados ([LICENSE](LICENSE)). Cada dato
que Terranova entrega conserva la licencia y la atribución de su fuente ([LICENSE-DATA.md](LICENSE-DATA.md)).
