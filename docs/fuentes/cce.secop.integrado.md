# SECOP Integrado, SECOP I y II (`cce.secop.integrado`)

Conjunto `rpmr-utcd` de datos.gov.co. Lo publica Colombia Compra Eficiente. Licencia CC BY-SA 4.0,
verificada el 2026-10-22. Se consulta en vivo.

## Qué publica

Los contratos de SECOP I y SECOP II en una sola tabla. Hay una fila por cada estado que tuvo un
contrato, así que el mismo contrato sale varias veces.

## Trampas medidas

1. **Sumar filas infla.** En Pitalito, en 2025, hay 1 748 filas y $174 000 millones. Contando cada
   contrato una vez, con su mayor valor, son 652 contratos y $63 157 millones. La herramienta
   cuenta cada contrato una vez.
2. **Sin fecha de firma no hay contrato firmado.** Las filas sin `fecha_de_firma_del_contrato`
   salen con `anio` vacío y son procesos que no llegaron a la firma. Medido el 2026-11-05 en la
   Gobernación del Huila (NIT 800103913), en SECOP II:

   | Estado | Filas | Valor |
   |---|---|---|
   | Borrador | 216 | $2,73 billones |
   | Cancelado | 106 | $2,86 billones |
   | Enviado al proveedor | 213 | $74 600 millones |
   | En aprobación | 4 | $49 millones |

   Son $5,7 billones que no se contrataron. Salen como los publica la fuente, con un aviso para
   no sumarlos con los años.
3. **Valores de digitación.** Hay contratos de 20 billones o más (uno de Medellín dice 440 000
   billones). No suman, y `contratos_valor_atipico` dice cuántos hubo.
4. **Va detrás de SECOP II.** En 2026 da 719 contratos de Pitalito contra 780 en SECOP II directo.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_integrado_contratos_entidad` | alto | contratos y valor por año y origen de una entidad por NIT, cada contrato una vez. Con aviso de las filas sin fecha de firma |

## Decisiones

- **2026-10-22:** etapa previa por contrato (su mayor valor) y luego el agregado por año.
- **2026-11-05:** las filas sin fecha de firma se quedan, con el aviso de que no son contratos
  firmados.
