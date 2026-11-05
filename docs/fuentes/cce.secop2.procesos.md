# SECOP II, procesos de contratación (`cce.secop2.procesos`)

Conjunto `p6dx-8zbt` de datos.gov.co. Lo publica Colombia Compra Eficiente. Licencia CC BY-SA 4.0,
verificada el 2026-10-22. Se consulta en vivo.

## Qué publica

Una fila por fase de un proceso de contratación de SECOP II, con:

- entidad, modalidad y precio base;
- estado y fecha de publicación;
- proveedores invitados y respuestas;
- el enlace al proceso.

## Identificadores

- `id_del_portafolio` (CO1.BDOS.…) es el proceso de compra. Es el que trae cada contrato.
- `id_del_proceso` (CO1.REQ.…) es una fase del proceso.
- Un proceso de compra puede tener varias fases. Medido en CO1.BDOS.2898382 (Pitalito, 2022):
  CO1.REQ.2978420, de presentación de observaciones, y CO1.REQ.3004001, de presentación de oferta.
  Los proponentes están en la fase de oferta.
- El identificador de un contrato (CO1.PCCNTR.…) no da nada aquí, y lo mismo pasa con uno de SECOP
  I. Medido el 2026-11-05.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_proceso_por_id` | alto | busca por proceso de compra o por fase; con «no encontrado», el aviso dice qué identificador sirve y que `secop_contrato_por_id` da el `id_proceso` de un contrato |

## Decisiones

- **2026-11-05:** aviso de «no encontrado» para el error común de pasar el identificador de un
  contrato.
