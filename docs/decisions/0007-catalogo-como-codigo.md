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
  - `uso_comercial: no` (licencias no comerciales): responde mientras Terranova sea gratuito y sin
    ingresos (ADR-0020), con aviso en `procedencia` de que el uso posterior debe ser no comercial.
    Si cambia ADR-0020, pasa a `licencia_no_habilitada`.
  - Licencias que no permiten redistribuir (SGC): la fuente no entra al catálogo.
- **Lista blanca, no lista negra:** solo salen los campos declarados; un campo nuevo en la fuente no
  sale hasta que alguien lo apruebe (protege de datos personales e inyección).
- **Validación (2026-10-21):** Compuerta reescrita para el modelo gratuito (ADR-0020); antes separaba llaves por uso comercial, una lógica de plan pago. El SGC queda fuera del catálogo, como dice CLAUDE.md.
