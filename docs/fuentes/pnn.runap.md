# PNN: Registro Único Nacional de Áreas Protegidas (`pnn.runap`)

Las áreas protegidas inscritas en el SINAP, del servicio ArcGIS de Parques Nacionales
(`mapas.parquesnacionales.gov.co/arcgis/rest/services/pnn/runap/MapServer`), con licencia CC BY-SA
4.0. Terrnova lo **copia** en PostGIS cada dos semanas, porque el servicio es lento.

| Fuente | Origen | Herramientas |
|---|---|---|
| `pnn.runap` | capa 0 del servicio RUNAP | `pnn_areas_protegidas_en_punto`, `pnn_areas_protegidas_en_zona`, `pnn_areas_protegidas_en_poligono` |

## Qué publica

Todas las áreas inscritas: parques nacionales, reservas forestales, distritos de manejo, parques
regionales y miles de reservas de la sociedad civil, de media hectárea a millones. Cada una con su
categoría de manejo, la autoridad ambiental, el área según el acto de declaratoria, la fecha de
inscripción y el polígono.

## Campos que importan

- `ap_nombre` y `ap_categoria`. Las categorías vienen en plural para unas («Reservas Forestales
  Protectoras Nacionales») y en singular para otras («Parque Nacional Natural»), como las escribe
  PNN.
- `organizacion`: la autoridad ambiental.
- `area_ha_total_resolucion`: el área del acto, no la del polígono. Va de 0,06 a 12 370 958 ha.
- `fecha_inscrita`: de 2011-06-30 a 2026-10-22.

## Cobertura

Todo el país, con las áreas inscritas. Un área declarada que no esté inscrita no aparece.

## Trampas medidas

1. **Orden alfabético.** En el cuadro de un grado alrededor de Bogotá, 169 áreas: primero «África»
   (4 ha), y Chingaza (77 290 ha) quedaba perdida en la lista.
2. **Las reservas de la sociedad civil son la mayoría.** En ese cuadro, 110 de 169, casi todas de
   pocas hectáreas.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `pnn_areas_protegidas_en_punto` | alto | sin cambios |
| `pnn_areas_protegidas_en_zona` | medio → alto | v2: de la más grande a la más pequeña, con `por_categoria` arriba |
| `pnn_areas_protegidas_en_poligono` | alto | sin cambios |

## Decisiones

- **2026-11-02, patrón E de la revisión de valor:**
  - `pnn_areas_protegidas_en_zona` se ordena por área del acto, de mayor a menor. Alrededor de
    Bogotá, primero Sumapaz (210 739 ha) y Chingaza.
  - El motor suma el derivado `conteo_por`, un diccionario {valor: cuántos}, de mayor a menor.
    Aquí va por categoría de manejo.

## Revisión de valor (2026-11-04)

- Probado en producción:
  - Chingaza (canario).
  - Un lote en los cerros de Bogotá: la Reserva Forestal Protectora Bosque Oriental de Bogotá,
    en punto y en polígono.
  - El cuadro de Bogotá: 169 áreas, Sumapaz primero, 110 reservas de la sociedad civil, en cuatro
    páginas con totales completos.
  - Bogotá urbano: vacío **sin aviso**. Ahora el vacío dice que un área declarada sin inscribir,
    o un suelo de protección del POT o del POMCA, no sale aquí.
- **Pendiente: cuánto del lote cae en cada área.** La herramienta de polígono dice que el lote
  «toca» el área, pero no cuántas hectáreas quedan adentro. La copia ya sabe calcularlo
  (`area_en_poligono`, como en el POMCA).
  - Falta una verdad medida para el canario. El servidor de PNN responde con un reto de
    Cloudflare desde la VPS y desde esta red, y no se pasan captchas.
  - Se mide en la copia cuando se rehaga desde Colombia, o con la herramienta ya desplegada, y
    entonces se graba la dorada.
