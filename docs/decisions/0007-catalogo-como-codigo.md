# ADR-0007 · Catálogo como código

- **Estado:** propuesta.
- **Decisión:** una entrada YAML por herramienta y por fuente, validada con Pydantic en CI
  (especificación en [specs/02-catalogo.md](../specs/02-catalogo.md)). Campos obligatorios: entidad competente, acto, URL, protocolo, **licencia SPDX y
  `uso_comercial: si|no|por_verificar`**, atribución, frescura, cobertura, **lista blanca de campos**,
  costo en créditos, consulta canaria con su verdad.
- **Compuerta de licencia en ejecución:** una fuente con `uso_comercial ≠ si` solo responde a llaves
  de plan `evaluacion`; las de producción reciben `licencia_no_habilitada`. El SGC queda `no`.
- **Lista blanca, no lista negra:** solo salen los campos declarados; un campo nuevo en la fuente no
  sale hasta que alguien lo apruebe (protege de datos personales e inyección).
