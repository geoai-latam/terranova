# invias.peajes · Tarifas de los peajes (INVÍAS)

## Revisión de valor (2026-11-04)

- Probado en producción:
  - «Río Frío» (canario).
  - «rio frio»: **vacío, en 12,7 s y sin aviso**. La búsqueda distinguía tildes.
  - «Siberia»: trae `lon` igual a `lat` (4.78035984). En un mapa, el peaje queda en África. Lo
    opera la Concesión Sabana de Occidente, aunque la descripción decía «solo peajes del
    INVÍAS».
- Arreglo:
  - la búsqueda sin tildes, con un `replace` anidado en la columna y `{nombre:ascii}`, probada
    en la fuente: «rio frio» encuentra «Río Frío»;
  - `maximo_valido: -66` en la longitud: una imposible sale vacía;
  - la descripción explica `responsable`;
  - un aviso de vacío.
