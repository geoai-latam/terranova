# ADR-0040 · Las páginas siguen en la fuente hasta el total

- **Estado:** aceptada (2026-11-05). Extiende la [ADR-0033](0033-listas-largas-por-paginas.md) y no
  cambia el contrato `rt/1` ([ADR-0005](0005-contrato-rt-1.md)). No toca la exportación de la
  [ADR-0038](0038-exportar-capas-desde-las-copias.md).
- **Contexto:**
  - El dueño armó un visor de infraestructura crítica con el MCP (2026-11-05). Las capas se
    cortaban en la fuente:
    - UPME: 1 000 de 2 192;
    - INVÍAS red vial: 500 de 659;
    - IDEAM estaciones: sin total.
  - La paginación de la ADR-0033 solo repartía, de 50 en 50, lo que ya había traído una consulta.
    Más allá del tope de la ficha no había forma de pedir el resto. El aviso decía «acote la
    búsqueda», que no sirve para pintar una capa entera.
  - El MCP también es una fuente rápida para construir visores y aplicaciones. Para eso, toda capa,
    geo o no, se tiene que poder bajar completa y con un total fiable.
- **Decisión:**
  1. **`pagina` cuenta sobre el total de la fuente.**
     - Las herramientas que devuelven una lista aceptan `pagina` y un `por_pagina` nuevo (1 a
       1 000; por defecto 50).
     - Una página no pasa del tope de la ficha. Con un tope de 10, las páginas son de 10.
     - Si la página cabe en lo que trae la consulta de siempre, sale de ella, igual que antes, y
       usa la caché.
     - Si pasa del tope, la puerta vuelve a la fuente con `desde` (la primera fila) y el tamaño de
       la página.
  2. **`desde` en las tres consultas que pueden seguir una lista.** Cada una mantiene un orden
     estable para que dos páginas no se crucen:

     | Consulta | Cómo sigue | Orden estable |
     |---|---|---|
     | `consultar_copia` | `OFFSET` | el orden de la ficha y, al final, la clave de la copia |
     | `datos_consultar` (Socrata) | `$offset` | `:id` o el orden de la ficha |
     | `arcgis_query_features` | `resultOffset` | OBJECTID; sin él no se sigue |

     No pagina en la fuente una herramienta con varias capas, consulta previa, complemento,
     agregados o un tope que sale de la entrada. Esa conserva la ADR-0033.
  3. **El total es el de la fuente en todas las páginas.** Sale del conteo, no del largo de la
     lista. Recorrer las páginas da exactamente el total, sin repetidos ni faltantes.
  4. **Los conteos y sumas de `datos` dicen sobre qué van.**
     - En una página que sale de la fuente, cuentan solo esa página.
     - En las que salen de la consulta de siempre, los primeros N.
     - El aviso de la página lo dice siempre. El aviso «vinieron N de total, acote» no sale en una
       página.
  5. **Una página que pasa del final** no es «no encontrado» ni «no hay nada en la zona»:
     - sale `encontrado`, con la lista vacía;
     - dice cuántas páginas hay;
     - sin el aviso de vacío de la ficha.
  6. **Cada página es una llamada y se cobra como tal.** No hay un cobro nuevo: bajar una capa de
     2 192 en páginas de 1 000 son tres consultas.
- **Consecuencias:**
  - Un visor baja la UPME entera en tres llamadas de 1 000, y un agente la recorre de 50 en 50 sin
    saltos.
  - Las páginas que pasan del tope no usan la caché de la consulta de siempre. Cada una tiene su
    propia entrada en la caché, con `desde` y `tope`.
  - Los conectores `datos-abiertos-mcp` y `arcgis-mcp` aceptan `desde`. Hay que reconstruir sus
    imágenes al desplegar.
  - Contra una fuente en vivo, una capa grande son varias peticiones, una por página y en el orden
    en que las pida quien llama. No es carga, pero el reparto de llamadas por minuto sigue
    aplicando. Lo masivo sigue siendo la exportación desde copias (ADR-0038).
- **Aceptación:**
  - `tests/test_paginas_fuente.py`: recorrer 2 192 elementos de 1 000 en 1 000 y de 50 en 50 da
    2 192 distintos, en orden.
  - Una página fuera de rango sale `encontrado` y vacía.
  - En producción, cada herramienta que se corta se recorre entera y la suma da el total medido
    en la fuente (tarea P0.3 del loop de revisión).
- **Alternativas descartadas:**
  - Subir los topes hasta la capa entera: no escala (SECOP, 26 000 contratos de Bogotá) y vuelve
    lenta la primera respuesta.
  - Dos niveles («bloque» de la fuente y página dentro del bloque): confunde a quien pagina.
  - Recalcular los derivados sobre toda la capa en cada página: es otra consulta de agregados por
    página. Se prefiere decir sobre qué van.
