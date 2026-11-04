# CAR Cundinamarca: rondas hídricas delimitadas (`car.rondas_delimitadas`)

Las rondas hídricas que la CAR Cundinamarca ya delimitó por acto administrativo. Están en un
servicio de ArcGIS Online de la CAR (`Delimitacion_Rondas`, capa 0), con licencia CC BY 4.0. Desde el
2026-11-03 se consultan en una copia de Terrnova.

## Qué publica

Medido el 2026-11-03, son 203 polígonos. Cada uno trae:

- `Fuente`: el nombre del cuerpo de agua;
- `Acto_Admin`: el acto que delimita la ronda;
- `Fecha`: la fecha del acto.

Los actos van de 2009 (río Bogotá, Acuerdos CAR 17 y 30) a 2023.

## Campos que importan

- **`Fuente`, el nombre, se escribe de varias formas:**
  - 66 rondas llevan el componente pegado: «Quebrada Carrizal - APCA» (33) y
    «Quebrada Carrizal - Faja Paralela» o «- Faja paralela» (33).
    - El APCA es el área de protección y conservación ambiental.
    - La faja paralela es la franja junto al cauce.
    - Son dos piezas de la misma ronda, con el mismo acto.
  - Dos nombres terminan en el municipio, no en un componente: «… - Suesca», «… - Sopó».
  - Uno repite el nombre en otra línea: «Quebrada Artesa \r\nQuebrada Artesa».
  - Uno viene vacío.
  - Algunos van con guion bajo: «Río Teusacá_parte alta».
- **`Acto_Admin`** a veces trae un espacio al final («Resolución 20237000965 de 2023 ») y a veces
  «Resolucion», sin tilde.

## Cobertura

Solo la jurisdicción de la CAR, y solo las rondas ya delimitadas. Muchos cuerpos de agua no tienen
aún su ronda, así que no encontrar una no quiere decir que no haya ronda.

## Trampas medidas

1. **Un punto casi nunca cae en una faja paralela**, que mide unos 30 m de ancho. Por eso la
   pregunta útil es por el polígono del lote.
2. **Polígonos enormes.**
   - Son decenas de miles de vértices, hasta 71 841 en la Quebrada Suralá.
   - En vivo se consultaban sin geometría.
   - La copia pesa 24 MB y no se simplifica, porque una faja de 30 m no aguanta 11 m de
     tolerancia.
3. **Tres polígonos inválidos de más de 50 000 vértices**, que la copia deja como vienen:
   - Quebrada Triste - APCA: se cruza a sí mismo;
   - Quebrada Suralá - APCA y su faja paralela: un componente con muy pocos puntos.

   El cruce por punto y por polígono responde sin error sobre ellos (medido). El área de un
   polígono que se cruza a sí mismo puede no ser exacta.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `car_ronda_hidrica_en_punto` | medio | v2: sobre la copia; `cuerpo_de_agua` y `componente` aparte, y aviso de vacío |
| `car_ronda_hidrica_en_poligono` | alto | v1: rondas que toca un lote, con `area_ha` de cada una y el total |

## Decisiones

- **2026-11-03, revisión de valor:**
  - **Copia:** se copia la capa (origen `arcgis`, clave `OBJECTID`, 20 por página, sin
    simplificar). Así se puede cruzar con el polígono de un lote y medir el área de ronda dentro.
  - **Nombre y componente:** `cuerpo_de_agua` y `componente` salen de `Fuente` con `patron`.
    - El componente se escribe de una forma, «APCA» o «faja paralela», con `valores`. Es una opción
      nueva del derivado `columna`.
    - El nombre tal como lo escribe la CAR sale en `nombre_en_la_fuente`.
  - **Medido en producción:**

    | Caso | Resultado |
    |---|---|
    | Canario del río Apulo (punto) | ronda 96 |
    | Quebrada Carrizal (punto) | ronda 168, APCA |
    | Chía (punto y lote) | sin ronda, con aviso |
    | Lote de ~350 m sobre el Apulo | 5,81 ha de ronda |
    | Lote en Aguas Claras | 2,27 ha de APCA y 0,17 ha de faja |
    | Lote en Suralá | 6,11 ha y 0,35 ha |
    | Lote en Quebrada Triste | 5,99 ha y 0,25 ha |

    Todos respondieron entre 17 y 180 ms.
- **Pendiente:** consultar por cercanía (radio). El polígono del lote ya contesta la pregunta de
  quien evalúa un predio.

## Revisión de valor (2026-11-04)

- Probado en producción:
  - el canario del río Apulo, en punto y en polígono;
  - un cuadro de ~4 × 4 km en Chía: cuatro rondas, del río Bogotá (82,6 ha), del río Frío
    (26,5 ha) y la quebrada Cuchua de Fagua, partida en APCA y faja paralela;
  - un punto urbano de Chía: vacío, con el aviso de que muchas rondas faltan por delimitar y de
    que la faja mide ~30 m.
- Faltaba lo que más pide quien mira un lote: **dónde** cae la ronda dentro de él. La herramienta
  de polígono daba las hectáreas sin forma, y la ronda entera son decenas de miles de vértices.
  - Ahora la copia sabe dar la geometría `recortada` (`ST_Intersection` con el polígono): solo la
    franja dentro del lote.
  - Sale como envolvente por defecto, y con `geometria: true` sale la forma.
- Falta medirlo en producción después del despliegue: la forma recortada del canario debe sumar
  las 5,81 ha que ya da `area_ha`.
