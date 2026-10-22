# ADR-0014 · Datos de personas

- **Estado:** propuesta.
- **Contexto:** los servicios de datos de gobierno suelen ofrecer ~15 consultas de personas por cédula o placa (antecedentes,
  afiliación, cédula vigente, SIMIT, RUNT). Varias pasan por formularios con captcha y todas tratan
  datos personales (Ley 1581, Decreto 1377, Ley 1266 para lo financiero). Nuestra política actual
  excluye datos personales y prohíbe saltar captchas.
- **Propuesta:** fuera del MVP; si se quiere competir ahí, es **otro producto** (KYC) con su base
  legal, rol de encargado del tratamiento, RNBD, oficial de datos, auditoría y contratos. Detalle y
  reglas en [specs/06-seguridad-y-datos.md](../specs/06-seguridad-y-datos.md).
