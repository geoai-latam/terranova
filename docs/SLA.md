# Acuerdo de nivel de servicio (SLA)

> **Borrador.** No es vinculante hasta que se publique junto con los términos de servicio. Las
> cifras salen de lo que hoy se mide (spec 05) y de un despliegue en un solo servidor (ADR-0030).
> El canal de soporte y la sonda ya están definidos.

## 1. Qué cubre

**Cubre:** la puerta de Terranova (`https://terrnova.com`), es decir, la API REST `/v1`, el MCP
(`/mcp` y sus perfiles) y las rutas de catálogo.

**No cubre la disponibilidad de las fuentes oficiales.** Son de terceros (entidades públicas
colombianas y organismos globales) y Terranova no las controla. Cuando una fuente falla, la puerta
responde «no se pudo» (`fuente_no_disponible`, `fuente_lenta`), no descuenta créditos y no inventa
el dato.

## 2. Disponibilidad objetivo

| Plan | Disponibilidad mensual de la puerta | Créditos de servicio |
|---|---|---|
| Gratis | sin compromiso (mejor esfuerzo) | no |
| Básico, Pro, Empresa, Escala | **99,5 %** objetivo | no |
| A medida (contrato anual) | la que se pacte; base 99,5 % | **sí** (sección 6) |

Un 99,5 % mensual admite hasta unas 3 h 39 min de indisponibilidad en un mes de 30 días.

## 3. Cómo se mide

- **Disponibilidad** = respuestas de la puerta que no son error propio ÷ total de respuestas del mes
  (hora UTC).
- **Error propio:** un 5xx de la puerta (`error_interno` o sin respuesta).
- **No cuentan como error propio:**
  - los 502 y 504 de una fuente (`fuente_no_disponible`, `fuente_respuesta_invalida`,
    `fuente_lenta`);
  - los 4xx (entrada, llave, saldo, tasa).
- Si la puerta no responde en absoluto, ese tiempo cuenta entero como indisponible.
- La medición sale de las métricas de la puerta y de una sonda externa (UptimeRobot), que consulta
  `https://terrnova.com/salud` cada 5 minutos desde fuera del servidor. Una consulta fallida
  cuenta como 5 minutos sin servicio.

**Fuentes:** el estado de cada una se publica en `/estado`, según su canario diario. Es
información, no un compromiso de disponibilidad.

## 4. Exclusiones

No cuentan como indisponibilidad:

- **Mantenimiento anunciado** con al menos 48 h de aviso, en la página de estado y por correo a
  los planes de pago. Se hace en horario de baja carga (hora de Colombia) y no pasa de 4 h al mes.
- **Fallas de las fuentes oficiales**, ver sección 1.
- **Uso fuera de los términos:** tráfico que excede la tasa de la llave, llaves revocadas o
  vencidas, saldo agotado.
- **Causas fuera de nuestro control razonable:** fallas del proveedor de red o de nube de alcance
  general, ataques de denegación de servicio, fuerza mayor.
- **Funciones marcadas** como beta o de evaluación, y las llaves `rt_test_`.

## 5. Atención de incidentes

| Severidad | Ejemplo | Primera respuesta | Actualizaciones |
|---|---|---|---|
| 1, crítica | la puerta no responde, o falla para todos | 1 h hábil (4 h fuera de horario en planes Empresa, Escala y A medida) | cada 2 h hasta resolver |
| 2, alta | una familia entera o una función clave falla; latencia muy por encima de lo normal | 4 h hábiles | diaria |
| 3, normal | una herramienta da un resultado erróneo o con formato incorrecto | 2 días hábiles | al cambiar el estado |
| 4, consulta | dudas de uso, documentación, solicitudes | 3 días hábiles | — |

- **Horario hábil:** lunes a viernes, de 8:00 a 18:00, hora de Colombia, sin festivos.
- **Plan Gratis:** soporte de mejor esfuerzo, sin tiempos garantizados.
- **Fuente caída** (fuera de nuestro control): se atiende como severidad 3. Se informa en
  `/estado` y, si se puede, se sirve una copia marcada como tal.
- **Canal de soporte:** soporte@terrnova.com. Incluya el `solicitud_id` de la respuesta afectada.

## 6. Créditos de servicio (solo A medida)

Si la disponibilidad mensual de la puerta queda por debajo de lo pactado, el cliente A medida
recibe un descuento sobre la cuota de ese mes:

| Disponibilidad del mes | Descuento |
|---|---|
| < 99,5 % y ≥ 99,0 % | 10 % |
| < 99,0 % y ≥ 95,0 % | 25 % |
| < 95,0 % | 50 % |

- **Cómo se pide:** por el canal de soporte, dentro de los 30 días siguientes al cierre del mes.
- **Cómo se paga:** el descuento se aplica a la siguiente factura y no se paga en efectivo.
- **Único remedio:** es el único remedio por incumplir la disponibilidad.

## 7. Cambios

- **Aviso:** cualquier cambio a este acuerdo se anuncia con 30 días de anticipación.
- **Contratos A medida:** conservan sus términos hasta que se renueven.
