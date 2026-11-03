# ICFES · Resultados únicos Saber 11

La fuente es `icfes.saber11` (datos.gov.co `kgxf-xxbe`). Sus herramientas son
`icfes_saber11_municipio`, `icfes_saber11_estrato_municipio` e `icfes_saber11_colegio`.

## Qué publica

- **Contenido:** los resultados del examen de Estado Saber 11, de 2010 a 2022, con **una fila por
  estudiante** y periodo: 7 109 704 filas. Trae puntajes, colegio, sede, municipio y variables del
  hogar.
- **Actualización:** la última carga es del 2023-08-23 y el portal declara frecuencia semestral.
  En la práctica no se actualiza desde entonces.
- **Licencia:** CC BY-SA 4.0, verificada el 2026-10-22.
- **Personas:** cada fila es un estudiante, la mayoría menores de edad. `estu_consecutivo` es un
  seudónimo del ICFES. Terrnova no lo copia ni lo devuelve, y solo publica grupos de 10 o más
  estudiantes (ADR-0014).

## Periodos (medido el 2026-11-03)

El periodo va como `AAAAS`: el año y luego el semestre del examen.

- **Semestre 1:** pocos colegios, sobre todo de calendario B. Son de 12 000 a 42 000 filas por año.
- **Semestre 2:** se codifica 2 hasta 2017 y 4 en 2019 y 2022. Es calendario A, la mayoría de los
  colegios: de 545 000 a 642 000 filas, y unos 1,07 millones en 20194 y 20224 por los repetidos.
- **Huecos:** faltan los segundos semestres de 2018, 2020 y 2021. No es un fallo de la copia: la
  fuente no los trae.

| Periodo | Filas |
|---|---|
| 20101 | 41 656 |
| 20102 | 628 374 |
| 20181 | 32 348 (no hay 20182) |
| 20194 | 1 096 524 |
| 20201, 20211 | 15 435, 15 528 (no hay segundo semestre) |
| 20224 | 1 065 888 |

## Campos de la copia

La copia guarda grupos: periodo, municipio, sede y estrato. No guarda estudiantes.

| Columna | Salida | Nota |
|---|---|---|
| `periodo` | `periodo` | AAAAS |
| `cole_cod_mcpio_ubicacion` | `municipio_divipola` | municipio de la sede |
| `cole_cod_dane_sede` | `codigo_dane_sede` | 12 dígitos |
| `fami_estratovivienda` | `estrato` | «Estrato 1» … «Estrato 6», «Sin Estrato» o vacío (218 219 filas sin respuesta) |
| `cole_nombre_sede` | `sede` | el mayor de los nombres del grupo, porque la escritura cambia entre años |
| `estudiantes` | `estudiantes` | cada estudiante una vez por periodo |
| `suma_<m>`, `n_<m>` | (no salen) | suma y número de datos de `punt_global`, `punt_matematicas` y `punt_lectura_critica` |

Los promedios se calculan como `sum(suma)/sum(n)`. Así pesan por estudiante, no por grupo, y dan
lo mismo que el promedio sobre los estudiantes únicos.

## Trampas medidas

1. **La fuente repite estudiantes** en 20181, 20194 y 20224, hasta 3 veces y con los mismos
   puntajes.
   - Contar filas daba 3 372 estudiantes en Chía 20224, cuando son 1 686.
   - En 20181 daba un promedio global de 317,0, cuando es 306,2.
   - La copia cuenta a cada estudiante una vez dentro de su periodo y toma su primera fila.
2. **Hasta 20141 no hay puntaje global ni de lectura crítica** (empiezan en 20142; matemáticas sí está desde 2010).
   - Son 2,6 millones de filas sin esos puntajes.
   - Ahí el promedio sale vacío, no en cero.
3. **Agregar en vivo era lento** (revisión de valor, patrón G).
   - La consulta en dos etapas, primero por estudiante y luego por grupo, tardaba unos 64 s en
     contar un municipio.
   - En frío pasó de 90 s, y los municipios grandes se caían por tiempo.
   - Además, cada pregunta recorría microdatos de menores.
4. **Bajar la fuente entera** toma unas 143 páginas de 50 000 filas.
   - Cada página de un periodo grande con `$order=:id` tardó 13,9 s y pesó 14,5 MB.
   - Se baja un periodo a la vez, una petición a la vez (ADR-0018).
5. **Estrato:** «Sin Estrato» es un valor que publica la fuente. Es distinto del vacío, que
   significa que el estudiante no respondió. La herramienta deja los dos como vienen.

## Decisiones

- **v2, 2026-11-03: copia preagregada** (origen `socrata_agregado`).
  - La copia guarda solo grupos, nunca `estu_consecutivo` ni una fila de estudiante.
  - Las tres herramientas leen la copia, con el promedio como cociente de sumas, el mínimo de 10
    estudiantes (`minimo: {"sum:estudiantes": 10}`) y dos decimales.
  - Una prueba exige ese mínimo en toda herramienta de la fuente.
- **Las verdades de los canarios salen de la fuente en vivo**, no de la copia:
  - Chía 20101: 464 estudiantes;
  - Chía 20224, estrato 1: 71 estudiantes, con promedio de 248,37;
  - sede 125175000493 en 20102: 153 estudiantes.
- **Pendiente:** buscar una sede por su nombre (`icfes_saber11_colegio` pide el código DANE).
