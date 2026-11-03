# ANI: concesiones viales (`ani.concesiones_viales`)

Una capa del servidor geográfico de la ANI (ANIscopio, `ModosANI/FeatureServer/3`), con licencia
CC BY-SA 4.0. Se consulta en vivo, por zona.

| Fuente | Capa | Herramientas |
|---|---|---|
| `ani.concesiones_viales` | `ModosANI/FeatureServer/3` («Carretero») | `ani_concesiones_viales_en_zona` |

## Qué publica

Un corredor por concesión vial nacional (47 en el país): proyecto, generación (1G a 5G), etapa,
concesionario, longitudes, avance de obra, fechas del contrato y valores. La red a cargo del INVÍAS
no está.

## Campos que importan

- `prcavn`: el avance de obra como **fracción de 0 a 1**. Vacío en los proyectos que no han empezado
  a construir.
- `fecrep`: la fecha del reporte del avance, en texto día/mes/año.
- `vlrcnt`: el valor del contrato **en pesos de su fecha de referencia** (`fecref`), no de hoy.
- `vlrcntix` y `fecindx`: el valor llevado a pesos de otra fecha (2021 en 34 de 47).
- `lngcnc`: la longitud concesionada, en metros.

## Cobertura

Medido el 2026-11-02:

- **la capa no se edita desde el 27 de septiembre de 2023**;
- el avance se reportó por última vez entre el 30 de octubre y el 30 de noviembre de 2022 (37 de
  47); 10 no tienen reporte.

## Trampas medidas

1. **«0,43» no decía que era 43 %.** La v1 daba el avance sin unidad ni fecha.
2. **El avance es de 2022.** Un proyecto que hoy está terminado puede salir con 0,43.
3. **Pesos de años distintos.** 12 contratos están en pesos de 2012, 11 de 2013, Briceño-Tunja-
   Sogamoso de 2000 y Armenia-Pereira-Manizales de 1996. Sumarlos o compararlos tal cual engaña.
4. **Un valor que no cuadra.** Armenia-Pereira-Manizales: 3 467 millones de pesos de 1996 y 1,43
   billones indexados a 2020, 412 veces más, cuando la inflación del periodo multiplica por unos 4.
   Se publica tal cual: no se sabe cuál de los dos está mal.
5. **Espacios duros en nombres** («Troncal del Magdalena C1» trae espacios sin corte).
6. **Corredores partidos en miles de piezas.** Medido el 2026-11-03, simplificado a ~55 m: IP
   Conexión Centro tiene 9 440 piezas (19 424 vértices), la Malla Vial del Valle 7 645 y Accesos
   Norte Fase II 7 138. Simplificar no junta piezas, así que el peso viene de esos tres. Las 47
   concesiones pesan 1,6 MB simplificadas; el canario (norte de Bogotá, cuatro), 323 KB, y completo,
   1,1 MB.
7. **La consulta devuelve el corredor entero,** no el tramo dentro del rectángulo: Briceño-Tunja-
   Sogamoso sale con sus 206 km aunque el rectángulo toque una punta.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `ani_concesiones_viales_en_zona` (v3) | alto | avance con su fecha, valor con la fecha de sus pesos y el indexado, aviso; corredor simplificado |

## Decisiones

- **2026-11-02, patrón D de la revisión de valor:**
  - Salen `avance_reportado_el`, `valor_contrato_pesos_de`, `valor_contrato_indexado` y
    `valor_indexado_a`.
  - Un aviso dice que el avance es una fracción, de 2022, y que los valores están en pesos de
    fechas distintas.
  - El avance se deja como fracción, como lo publica la fuente: se aclara, no se transforma.
- **2026-11-03, revisión de valor (v3):** sale el corredor de cada concesión, simplificado a ~55 m
  (`geometria: simplificada`). Responde en 1 a 2 s. La descripción dice que es el corredor entero y
  que sirve para verlo en un mapa, no para medir.
