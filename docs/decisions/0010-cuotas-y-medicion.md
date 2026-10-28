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
- **Enmienda (2026-10-27): créditos por tipo de pregunta.**
  - **Contexto:** la regla «en vivo 10, copia 1» no se cumplía. Cada ficha traía un número puesto a
    mano (1, 2, 3, 5, 10 o 20), el ejecutor lo cobraba sin mirar `servido_desde` y nada lo validaba.
    Había consultas en vivo a 2 y herramientas servidas desde copia a 10.
  - **Decisión:** el crédito depende del tipo de pregunta, no de cómo la puerta trae el dato. Cada
    herramienta declara su `cobro` y la tarifa sale de `TARIFA` (`src/terranova/catalogo.py`):

    | `cobro` | Créditos | Tipo de pregunta |
    |---|---|---|
    | `codigo` | 1 | de nombre a código y buscador del catálogo |
    | `registro` | 2 | un registro o una serie simple (por id, NIT, código) |
    | `agregado` | 5 | agregados o búsqueda de texto (por municipio, por año) |
    | `punto` | 10 | espacial en un punto |
    | `zona` | 20 | espacial en una zona o ráster |

    `ficha_lugar` sigue costando la suma de sus partes, con tope de 50. Las fallas, la caché y
    `fuera_de_cobertura` siguen sin descontar.
  - **Por qué no por modo:** pasar una fuente a copia (ADR-0024) no debe cambiar su precio, y lo
    territorial, que es lo que más valor tiene, no debe quedar como lo más barato por estar en copia.
  - **Validación:** el catálogo rechaza un `cobro` espacial en una operación que no lo es, y uno no
    espacial en `en_punto` o `en_zona` (un ráster en un punto se cobra como `zona`). El promedio del
    catálogo pasa de 4,43 a 4,33 créditos por consulta.
