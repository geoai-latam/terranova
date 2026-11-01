# ADR-0007 · Catálogo como código

- **Estado:** aceptada (2026-10-21).
- **Decisión:** una entrada YAML por herramienta y por fuente, validada con Pydantic en CI
  (especificación en [specs/02-catalogo.md](../specs/02-catalogo.md)). Campos obligatorios: entidad competente, acto, URL, protocolo, **licencia SPDX y
  `uso_comercial: si|no|por_verificar`**, atribución, frescura, cobertura, **lista blanca de campos**,
  costo en créditos, consulta canaria con su verdad.
- **Compuerta de licencia en ejecución** (ajustada al modelo gratuito de ADR-0020):
  - `uso_comercial: si`: responde a todas las llaves.
  - `uso_comercial: por_verificar`: solo responde a llaves de plan `evaluacion`; las demás reciben
    `licencia_no_habilitada`. Una fuente sin licencia verificada no sale a producción.
  - `uso_comercial: no` (licencias no comerciales): responde mientras Terrnova sea gratuito y sin
    ingresos (ADR-0020), con aviso en `procedencia` de que el uso posterior debe ser no comercial.
    Si cambia ADR-0020, pasa a `licencia_no_habilitada`.
  - Licencias que no permiten redistribuir (SGC): la fuente no entra al catálogo.
- **Lista blanca, no lista negra:** solo salen los campos declarados; un campo nuevo en la fuente no
  sale hasta que alguien lo apruebe (protege de datos personales e inyección).
- **Validación (2026-10-21):** Compuerta reescrita para el modelo gratuito (ADR-0020); antes separaba llaves por uso comercial, una lógica de plan pago. El SGC queda fuera del catálogo, como dice CLAUDE.md.

## Enmienda (2026-11-01): una llave de producción ve y usa solo lo vendible

- **Contexto:** la ADR-0029 reemplazó a la ADR-0020 y el sitio ya publica precios, así que se
  cumple la condición de arriba («si cambia ADR-0020, pasa a `licencia_no_habilitada`») y la de la
  excepción de la DIAN («se decide antes del primer cobro»). Además, `/mcp`, `/v1/herramientas` y
  `/llms.txt` listaban 207 herramientas mientras el sitio anunciaba 205: la DIAN de usuarios
  aduaneros (sin uso comercial) y `catalogo_buscar` (borrador, licencia por verificar), que a una
  llave de producción le respondía `licencia_no_habilitada`.
- **Decisión:**
  - **Vendible** = fuente `publicada` con `uso_comercial: si` (`catalogo.vendible`).
  - Una llave de producción (`rt_live_`, plan `normal`; también la llave de prueba del alta) solo
    usa lo vendible. Lo demás (por verificar, sin uso comercial aunque tenga
    `excepcion_uso_comercial`, borrador) responde `licencia_no_habilitada` y no llama a la fuente.
    Las fichas lo saltan con un aviso.
  - Lo que no puede usar no se le ofrece: `tools/list` de `/mcp` y de cada perfil, y
    `buscar_herramienta` de `/mcp/catalogo`, filtran según la llave.
  - Una llave de evaluación (`rt_test_`, interna) sigue viendo y usando todo el catálogo: es como se
    prueban las fuentes antes de promoverlas, y los canarios corren con ese plan.
  - Lo que se anuncia sale de `catalogo_vendible`: `/v1/herramientas`, `/v1/fuentes`, `/v1/estado`,
    `/estado`, `/llms.txt`, la tarjeta MCP, `docs/HERRAMIENTAS.md` y el OpenAPI (las rutas REST no
    vendibles existen para evaluación, pero no salen en él). El sitio (`web/construir.py`) cuenta lo
    mismo; `tests/test_vendible.py` lo compara.
- **Consecuencia:** la DIAN de usuarios aduaneros queda solo para evaluación. Para volver a
  venderla hace falta permiso escrito de la DIAN; si no llega, sale a borrador.
