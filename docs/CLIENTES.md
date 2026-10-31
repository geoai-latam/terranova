# Guía para clientes

Terrnova es una sola puerta, por REST y por MCP, a fuentes oficiales colombianas y globales. Hoy son
207 herramientas sobre 180 fuentes. Cada respuesta llega en el mismo sobre `rt/1`, que dice:

- de qué fuente sale el dato;
- con qué licencia;
- si está completo;
- si se sirvió en vivo o desde una copia.

Puerta: `https://terrnova.com`. Los precios y el alta están en el portal de planes, no en esta guía.

## 1. Inicio rápido

1. **Pida su llave.** Llega una sola vez, por un canal privado. Guárdela como un secreto (variable
   de entorno, gestor de secretos) y no la ponga en el código ni en un repositorio.
2. **Haga la primera consulta.** Por ejemplo, el código DIVIPOLA de un municipio por su nombre
   (1 crédito):

   ```bash
   export TERRNOVA_LLAVE=rt_live_...
   curl -s -X POST https://terrnova.com/v1/co/territorio/dane_divipola_buscar \
     -H "Authorization: Bearer $TERRNOVA_LLAVE" \
     -H "Content-Type: application/json" \
     -d '{"nombre":"Cali"}'
   ```

   La respuesta trae `"estado":"encontrado"`, los municipios que coinciden con su código en
   `datos.elementos`, y la fuente (DANE) con su licencia en `procedencia`.

   - **Tildes:** la búsqueda las respeta. «Bogota» no encuentra «Bogotá».
   - **Windows:** si la terminal no manda el cuerpo en UTF-8, guárdelo en un archivo y envíelo
     con `--data-binary @consulta.json`.
3. **Mire su saldo:**

   ```bash
   curl -s https://terrnova.com/v1/uso -H "Authorization: Bearer $TERRNOVA_LLAVE"
   ```

### Qué herramienta usar

| Para | Dónde |
|---|---|
| Lista de herramientas: pregunta, familia, fuente, créditos y ruta | `GET /v1/herramientas` |
| Lo mismo, en texto para agentes | `GET /llms.txt` |
| Esquema OpenAPI con la entrada de cada herramienta | `GET /openapi.json` (navegable en `/docs`) |
| Ficha técnica de una fuente: cobertura, campos, actualización, alertas | `GET /v1/fuentes/{fuente_id}` |
| Buscar en el catálogo por tema | herramienta `catalogo_buscar` (familia `meta`) |

Las rutas de catálogo son públicas y no gastan créditos. Las herramientas siguen el patrón
`POST /v1/co/<familia>/<herramienta>`, con la entrada en JSON. La ficha de un lugar está en
`POST /v1/fichas`.

### Por MCP (agentes y asistentes)

La puerta habla MCP por *streamable HTTP*, con la misma llave en la cabecera `Authorization`.
Hay tres entradas, con las mismas herramientas por debajo:

- **`/mcp`:** todas las herramientas (más de 200).
- **`/mcp/<familia>`:** un perfil con las de una sola familia, de 14 a 47 herramientas. Las
  familias son:
  - `territorio`, `contratacion`, `empresas`, `normativa`, `justicia`, `estadisticas` y
    `ambiente`;
  - `meta`, el buscador del catálogo.
- **`/mcp/catalogo`:** pocas herramientas genéricas. `buscar_herramienta` encuentra la que
  responde la pregunta, con su entrada, y `consultar` la ejecuta.

**Cuál usar según su cliente** (medido con el banco de escala, ADR-0031):

| Cliente | Use | Por qué |
|---|---|---|
| Claude Code, Claude Desktop (con `mcp-remote`), Cursor, VS Code ≥ 1.118 | `/mcp` o un perfil | buscan herramientas por su cuenta: con `/mcp` aciertan igual que con un perfil y gastan ~35 000 tokens por pregunta |
| La API de OpenAI y su Agents SDK, Windsurf, n8n, Zapier, LangChain, Copilot Studio | `/mcp/catalogo` | no buscan herramientas o tienen tope (Windsurf 100, modelos de OpenAI 128); el catálogo cuesta lo mismo aunque el catálogo crezca (~10 000 tokens) |
| Un caso de uso de un solo dominio (catastro, contratación…) | `/mcp/<familia>` | lo más preciso y lo más rápido: el modelo ve solo las herramientas de su tema |

**claude.ai y la interfaz web de ChatGPT todavía no conectan:** sus conectores remotos piden
OAuth, y Terrnova usa una llave en la cabecera `Authorization`. OAuth está en el plan. Mientras
tanto, use Claude Desktop con `mcp-remote` o la API.

Opus 5.5 y gpt-5.4-mini acertaron lo mismo en los tres modos: lo que cambia entre ellos es el costo
en contexto, no la precisión.

- **En todos los perfiles:**
  - las herramientas de nombre a código (DIVIPOLA, entidades de SECOP);
  - `fuente_describir`, que da la ficha técnica de una fuente y no gasta créditos.
- **La ficha de un lugar:** en `/mcp`, `/mcp/territorio` y por `consultar` en `/mcp/catalogo`.
- **Geometría:** por MCP, como por REST, cada polígono llega como su envolvente (`bbox`). Pida
  `geometria: true` solo si va a dibujar la forma completa: un polígono pesa de 20 a 300 KB y la
  mayoría de los clientes no se lo pasan al modelo.
- **Listas largas:** si `datos.elementos` pasa de 50, llega por páginas de 50 (ADR-0033), con un
  aviso que dice cuántos hay y cómo pedir la siguiente (`pagina: 2`). Los totales y agregados de
  `datos` cuentan la lista completa.
- **Tarjeta del servidor:** la estándar (SEP-2127) en `/mcp/server-card`, con el catálogo de IA
  en `/.well-known/ai-catalog.json`; la propia, con perfiles y herramientas, en
  `/.well-known/mcp/server-card.json`. En el registro oficial de MCP, el servidor es
  `com.terrnova/terrnova` (`server.json` en la raíz del repo).

Cursor y otros clientes que aceptan `url` y `headers` (`mcp.json`):

```json
{
  "mcpServers": {
    "terrnova": {
      "url": "https://terrnova.com/mcp/territorio",
      "headers": { "Authorization": "Bearer rt_live_..." }
    }
  }
}
```

Claude Code:

```bash
claude mcp add --transport http terrnova https://terrnova.com/mcp \
  --header "Authorization: Bearer $TERRNOVA_LLAVE"
```

Claude Desktop y otros clientes que solo hablan por stdio, con el puente `mcp-remote`. La
cabecera va sin espacios dentro de `args` (con espacios falla en Windows); el `Bearer` va en la
variable:

```json
{
  "mcpServers": {
    "terrnova": {
      "command": "npx",
      "args": ["mcp-remote", "https://terrnova.com/mcp/ambiente",
               "--header", "Authorization:${TERRNOVA_AUTH}"],
      "env": { "TERRNOVA_AUTH": "Bearer rt_live_..." }
    }
  }
}
```

## 2. Llaves

| Prefijo | Para qué | Qué ve |
|---|---|---|
| `rt_live_` | producción | las fuentes con licencia verificada para uso comercial |
| `rt_test_` | evaluación, con fecha de vencimiento | además, las fuentes con licencia todavía por verificar, con aviso |

- **Alcance:** cada llave tiene sus familias. Una herramienta fuera de ellas responde 403
  `sin_permiso`.
- **Licencia:** una fuente que su llave no puede ver responde 403 `licencia_no_habilitada`.
- **Llave filtrada:** avísenos. La revocamos y le enviamos otra; su saldo y su plan siguen igual.

## 3. Créditos

Cada consulta descuenta créditos según **el tipo de pregunta**, no según cómo se trae el dato: que
una fuente pase a servirse desde una copia no cambia su precio. Cada herramienta dice su costo en
`/v1/herramientas` (`creditos`).

| Créditos | Tipo de pregunta | Ejemplos |
|---|---|---|
| 1 | de nombre a código; buscador del catálogo | DIVIPOLA por nombre, entidades de SECOP de un municipio |
| 2 | un registro o una serie simple (por id, NIT o código) | un contrato de SECOP, un predio por código |
| 5 | agregados o búsqueda de texto | contratos de una entidad, delitos por municipio, normas por texto |
| 10 | espacial en un punto | predio, vereda o área protegida en un punto |
| 20 | espacial en una zona o en un ráster | áreas protegidas en una zona, cobertura del suelo, sismos |
| hasta 50 | ficha de un lugar | la suma de sus partes |

**No descuentan:**

- las respuestas desde la caché (`servido_desde: cache`);
- `fuera_de_cobertura`;
- los errores, incluido «no se pudo» (fuente caída o lenta);
- las rutas de catálogo.

`creditos` en cada sobre dice cuánto costó esa consulta.

**Saldo del mes:** `GET /v1/uso` responde así:

```json
{"org": "su-org", "nivel": "pro", "plan": "normal", "mes": "2026-10",
 "limite": 110000, "usados": 41230, "disponibles": 68770,
 "reinicia": "2026-11-01T00:00:00+00:00"}
```

El saldo se renueva el **día 1 de cada mes (00:00 UTC)** y **no se acumula**: lo que no se gasta
en el mes se pierde. Si sube de plan, el límite nuevo aplica desde la siguiente consulta y lo ya
usado en el mes se mantiene.

## 4. Respuestas

### El sobre `rt/1`

Toda consulta que llega a la fuente devuelve un sobre con `estado`:

| `estado` | Qué significa | ¿Descuenta? |
|---|---|---|
| `encontrado` | la fuente respondió y hay datos | sí |
| `no_encontrado` | la fuente respondió y **no hay** datos para esa entrada | sí |
| `fuera_de_cobertura` | la entrada está fuera de lo que cubre la fuente (otro país, otro periodo) | no |
| `parcial` | una consulta compuesta (la ficha de un lugar) con partes que fallaron; cada falla está en `errores` | solo lo que respondió |

**«No encontrado» no es «no se pudo».** Cuando la fuente no responde, no llega un sobre vacío sino
un error (ver abajo). Terrnova nunca inventa un dato ni hace pasar uno viejo por actual.

Campos del sobre:

| Campo | Contenido |
|---|---|
| `datos` | el resultado. Una lista de más de 50 elementos llega por páginas (`pagina: 2`, …); sus totales cuentan todos |
| `huella` | `sha256` de `datos`, para verificar que no cambió |
| `avisos` | lo que debe saber: total desconocido, datos no recientes, copia vencida… |
| `geo_result` | las geometrías, en EPSG:4326 (lon, lat). Los puntos llegan completos; cada polígono o línea, como su envolvente (`bbox`, con `geometry: null`). Cada rasgo lleva en `properties.elemento` su posición en `datos`, salvo que pida `geometria: true` |
| `procedencia` | una entrada por fuente consultada (detalle abajo) |

Cada entrada de `procedencia` trae:

- `entidad`, `url` y `acto` (la norma que le da la competencia a la entidad);
- `licencia` (`spdx`, `url`, `uso_comercial`) y la `atribucion` que debe citar;
- `servido_desde`: `fuente` (en vivo), `copia` (copia del bulk oficial), `curado`, `cache` u
  `obsoleto` (una copia vieja servida porque la fuente no respondió; siempre con aviso);
- `consultado_en`, `version_dataset`, la `consulta` hecha a la fuente;
- `completitud`: `vistos`, `total` y `truncado`;
- `cache`: `acierto` y `edad_s`.

Al publicar o reutilizar un dato, **cite la atribución y respete la licencia de su fuente**. Por
ejemplo, CC BY-SA exige compartir igual.

### Errores

Los errores llegan en `application/problem+json` (RFC 9457), con un `code` estable y el
`solicitud_id` que debe darnos si escribe a soporte (soporte@terrnova.com, de lunes a viernes de
8:00 a 18:00, hora de Colombia):

| HTTP | `code` | Qué hacer |
|---|---|---|
| 400 | `parametro_invalido`, `zona_demasiado_grande` | corregir la entrada; `param` dice cuál |
| 401 | `no_autenticado` | falta la llave o no es válida |
| 402 | `saldo_agotado` | se acabaron los créditos del mes; el mensaje dice cuándo se renuevan (y dónde subir de plan) |
| 403 | `sin_permiso`, `licencia_no_habilitada` | la llave no cubre esa familia o esa fuente |
| 404 | `no_existe` | la herramienta o la fuente no existe (sugiere ids parecidos) |
| 429 | `limite_tasa` | demasiadas consultas seguidas: espere lo que dice `Retry-After` (segundos) |
| 502 | `fuente_no_disponible`, `fuente_respuesta_invalida` | **no se pudo**: la fuente oficial falló; reintente más tarde |
| 504 | `fuente_lenta` | **no se pudo**: la fuente no respondió a tiempo |
| 500 | `error_interno` | falla nuestra; escríbanos con el `solicitud_id` |

**Tasa:** cada llave tiene una ráfaga de 20 consultas y repone 60 por minuto. Las cabeceras
`RateLimit` y `RateLimit-Policy` dicen cuánto le queda. Reintente con espera creciente, nunca en
bucle cerrado.

## 5. Estado del servicio

- **`/estado`:** página pública con el estado de la puerta y el de cada fuente según su último
  canario diario.
- **`GET /v1/estado`:** lo mismo en JSON.

Las fuentes son de entidades públicas: cuando una falla, la verá en rojo y la puerta responderá
«no se pudo». El compromiso de servicio está en [SLA.md](SLA.md).
