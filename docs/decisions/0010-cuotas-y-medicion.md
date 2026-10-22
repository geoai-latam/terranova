# ADR-0010 · Cuotas y medición

- **Estado:** propuesta.
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
  - 402 al agotar el saldo; 429 con `Retry-After` al exceder la tasa; encabezados `RateLimit-*`.
- **Niveles gratuitos propuestos:**

  | Nivel | Créditos al mes | Para |
  |---|---|---|
  | con llave | 20 000 | cualquiera |
  | ampliado | 200 000 | entidades públicas, academia, proyectos abiertos (a pedido) |

- **Más adelante:** si algún día se cobra, el medidor ya existe y la pasarela se decide entonces.
