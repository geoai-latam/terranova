# Estrategia de pruebas y E2E

## 11.1 Pirámide

| Nivel | Qué cubre | Herramienta | Dónde corre |
|---|---|---|---|
| Unidad y propiedad | invariantes `rt/1`, mapeo, saneamiento, catálogo | pytest + Hypothesis | cada commit |
| Contrato | JSON Schema `--check`, catálogo, `outputSchema` | pytest | cada commit |
| Dorada (fuente grabada) | cada herramienta contra respuestas reales grabadas | pytest-recording (sin llaves en cassettes) | cada commit; regrabación semanal |
| API | OpenAPI con casos generados | Schemathesis | cada PR |
| MCP | cliente FastMCP en memoria, snapshots de esquemas y salidas | FastMCP `Client(server)` + inline-snapshot | cada PR |
| Paridad | REST ≡ MCP por herramienta | pytest | cada PR |
| E2E de sistema | compose completo, flujos de la sección E2E | pytest + clientes reales | antes de cada gate y cada release |
| En vivo (canario) | verdad medida por herramienta | runner propio | diario en el servidor |
| Agente | banco de preguntas de compradores | runner + LLM real (modelo mini, pocas corridas con el grande) | por ola y por release |
| Navegador | GEO Copilot sobre la puerta | Playwright | antes de M1/M2 |
| Carga | caché y fuente simulada | k6 | antes de M1/M2 |
| Seguridad | permisos, revocación, inyección, abuso | pytest + revisión OWASP MCP Top 10 | antes de M1/M2 |

**Regla:** nunca se golpean servidores del Estado en pruebas de carga; carga solo contra caché y
fuentes simuladas.

## 11.2 Pruebas de propiedad del contrato

Las 10 reglas del contrato como propiedades Hypothesis sobre sobres generados y sobre todas las salidas
doradas.

## 11.3 Pruebas doradas

Por herramienta: entrada del canario + respuesta grabada → sobre esperado (snapshot). Regrabación
semanal programada: si cambia el esquema de la fuente, falla aquí antes que en producción.

## 11.4 Canarios en vivo

Por herramienta: entrada fija, verdad medida (valor exacto o rango), latencia máxima, y verificación
del esquema. Resultado: `verde | lento | roto | caido`. Alimenta el SLI de correctitud y la página de
estado.

## 11.5 Escenarios E2E de sistema

| # | Escenario | Pasa si |
|---|---|---|
| E2E-01 | Crear org y llave por CLI → llamar `igac_predio_en_punto` por REST | 200, `rt/1` válido, verdad de Chía, licencia del ítem, 10 créditos descontados |
| E2E-02 | La misma llamada por MCP (cliente FastMCP y Claude Code) | misma huella que E2E-01 |
| E2E-03 | Llave revocada | 401 en < 5 s tras revocar, por REST y MCP |
| E2E-04 | Saldo agotado y exceso de tasa | 402 con saldo 0; 429 con `Retry-After`; sin sobreconsumo concurrente |
| E2E-05 | Fuente caída (conector detenido) | `fuente_no_disponible` rápido; no descuenta; con caché previa: `obsoleto` + aviso |
| E2E-06 | Fuente sin licencia comercial con llave de producción | `licencia_no_habilitada`; con llave de evaluación responde |
| E2E-07 | Ficha del predio de Chía | todas las partes con procedencia; verdades; p95 < 15 s |
| E2E-08 | Ficha con una parte caída | `parcial`, error de esa parte, las demás completas |
| E2E-09 | Bogotá en catastro IGAC | `fuera_de_cobertura`, no descuenta |
| E2E-10 | Reintento con el mismo `Idempotency-Key` | un solo evento de uso |
| E2E-11 | GEO Copilot en navegador: «¿qué predio y qué restricciones tiene este punto?» | responde con la ficha, pinta el predio, «Cómo lo hice» muestra fuentes y licencias |
| E2E-12 | Lote de 50 códigos prediales con 3 inválidos (M2) | 47 resultados + 3 errores por ítem; descuento por ítem válido |
| E2E-13 | Trabajo lento con `Prefer: wait=5` (M2) | 202 + `status_url`; el estado no descuenta; termina con el sobre |
| E2E-14 | Inyección en texto de la fuente (cassette con instrucciones y bidi) | sale saneado y solo dentro de `datos` |

## 11.6 Banco de agente

- 60 preguntas de compradores reales (sin nombres de clientes) en cinco familias, cada una con su
  verdad medida y la herramienta esperada.
- Métricas: tasa de éxito, tasa de herramienta correcta, llamadas por tarea, tokens, latencia; con
  `/mcp` completo y con perfil.
- Corre con LLM real; cada resultado se revisa críticamente, no solo el verde.
