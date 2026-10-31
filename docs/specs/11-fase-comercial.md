# Spec 11 · Fase comercial (F8)

*2026-10-31.* Sale de la auditoría integral del mismo día. La puerta está en producción, pero el
embudo convierte cero y no hay demanda documentada. F8 pone a prueba la capa de datos y las
soluciones de encima con compradores reales, antes de seguir sumando fuentes.

## Qué se deja de hacer mientras dura F8

- Olas nuevas de fuentes sin pedido. Una fuente entra solo si la pide un prospecto con su caso de
  uso, o si cierra un hueco de confianza (latencia, copia, licencia). El modelo operativo está en
  [PLAN_EXPANSION.md](../PLAN_EXPANSION.md#modelo-operativo-de-la-expansión).
- Segundo país, pagos de agentes (x402) y rediseños del sitio fuera de lo que pidan los datos.

## Specs

| Spec | Qué | Aceptación | Tamaño |
|---|---|---|---|
| F8.1 | El embudo funciona de punta a punta: correo de soporte que recibe, alta de la llave de prueba con correo verificado ([ADR-0034](../decisions/0034-alta-con-correo-verificado.md)) y formulario de contacto | una persona de fuera pide y usa su llave sin intervención; el mensaje de contacto llega | S |
| F8.2 | Quién vende y bajo qué términos: entidad que factura, términos, privacidad y SLA publicados (ADR-0029) | las tres páginas publicadas sin «en revisión»; razón social en el pie | M (humano) |
| F8.3 | Registro de prospectos: sector, dolor, herramienta o solución, objeción y siguiente paso (fuera del repo, en `interno/`) | 40 prospectos registrados; 20 conversaciones con nota | M (humano) |
| F8.4 | Pilotos a precio fijo: una solución entregada con la capa de datos (revisión, tablero, alertas o asistente), con horas medidas y lo que deja en el catálogo | 2 pilotos entregados; cada uno deja una herramienta, ficha o plantilla reutilizable | L |
| F8.5 | Métricas del embudo cada viernes, de fuentes que existen: visitas y clics (analítica sin cookies), llaves nuevas por semana y por origen, tiempo hasta la primera llamada, activación (≥ 10 llamadas exitosas en 7 días), llaves activas a 7 y 28 días | las métricas salen de la base y de la analítica, no a mano | M |
| F8.6 | Distribución: el servidor en el registro oficial de MCP y en directorios, con la tarjeta del servidor estándar | aparece al buscar «terrnova» en el registro | S |

## Gate F8

- 2 pilotos cobrados o una propuesta firmada.
- 150 llaves de prueba con correo verificado y una activación ≥ 40 %, o la lección escrita de por
  qué no.
- Las fuentes que se sumaron durante F8 tienen el pedido que las justificó.

Las metas son un supuesto inicial sin línea base. Se revisan a los 30 días con lo medido.
