# ADR-0010 · Cuotas y medición

- **Estado:** aceptada (2026-10-21).
- **Decisión:**
  - La unidad de consumo es el **crédito**, como en otros servicios de datos de gobierno, para poder comparar:
    - `en_vivo` cuesta 10;
    - `copia` y `curado` cuestan 1;
    - `ficha_lugar` cuesta la suma de sus partes, con tope;
    - **las fallas y los aciertos de caché no descuentan**.
  - Todo es gratis al inicio (ADR-0020). Los créditos **protegen las fuentes del Estado y reparten la
    capacidad (y el gasto)**; no sirven para cobrar.
- **Mecánica:**
  - Tasa por llave con token bucket en Redis (script atómico) y saldo mensual en Postgres.
  - Un evento de uso por solicitud (`solicitud_id` único) en un outbox. La medición nunca hace fallar
    la respuesta.
  - 429 tanto al exceder la tasa (`limite_tasa`) como al agotar el saldo del mes (`saldo_agotado`),
    siempre con `Retry-After` (para el saldo, hasta el reinicio del mes) y encabezados `RateLimit-*`.
    No se usa 402: el servicio es gratuito (ADR-0020) y no hay nada que pagar.
- **Niveles gratuitos propuestos:**

  | Nivel | Créditos al mes | Para |
  |---|---|---|
  | con llave | 20 000 | cualquiera |
  | ampliado | 200 000 | entidades públicas, academia, proyectos abiertos (a pedido) |

- **Más adelante:** si algún día se cobra, el medidor ya existe y la pasarela se decide entonces.
- **Validación (2026-10-21):** Cambiado 402 → 429 `saldo_agotado`: en un servicio gratuito no hay nada que pagar. Spec 01, E2E-04 y F3.3 quedan alineados.
