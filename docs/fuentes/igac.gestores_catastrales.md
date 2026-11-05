# IGAC, gestores catastrales de Colombia (`igac.gestores_catastrales`)

## Qué publica

- Una fila por municipio (1 122) con la entidad que hace su catastro, en datos.gov.co
  (`bhcx-bx97`). Licencia CC BY-SA 4.0.
- Frecuencia declarada anual. Sin cambios desde el 2025-03-05 (ficha cosechada el 2026-10-22).
- `responsabl` y `contacto` (personas) no salen (ADR-0014).

## Trampas medidas (2026-11-05)

1. **La lista puede estar vieja frente a las otras fuentes del IGAC.** Yopal (85001) sale con
   «IGAC», «EN OPERACION». Pero la base catastral pública del IGAC (corte 06_2026) no tiene
   ningún predio de Yopal en el registro 1, y las estadísticas catastrales de 2025 dicen
   «Municipio de Sabanalarga» como gestor (las de 2017 a 2024 dicen IGAC). No se sabe cuál de las
   dos tiene razón; se deja como lo publica cada una.
2. Bogotá (UAECD) y Chía (IGAC) cuadran con la base catastral.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `igac_gestor_catastral_municipio` | medio | responde en 2–8 s; un aviso dice la fecha de la lista y el caso de Yopal |

## Decisiones

- **2026-11-05, revisión de valor:** el aviso de «datos no recientes» del motor no sale (la
  frecuencia es anual y aún no pasan dos años), pero la lista ya no cuadra en Yopal. Se avisa en
  cada respuesta con la fecha y el caso medido.
