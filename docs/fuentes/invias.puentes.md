# invias.puentes

## Revisión de valor (2026-11-04)

- Probado en producción: el canario (Bavaria, 1926, acero) y el norte del Tolima: 23 puentes de
  Ibagué - Mariquita, con material y sistema estructural traducidos.
- `fecha_inspeccion` salía «2012.07.07». Ahora sale en ISO, con un orden de fecha nuevo, `amd`.

## Capa entera para un visor (2026-11-05)

- Medido en datos.gov.co (`nsdj-ep2p`): 2 830 puentes; las 3 páginas de 1 000 de
  `invias_puentes_en_zona` con el rectángulo del país dan 2 830, sin faltantes.
- La herramienta no traía identificador. La fuente repite 13 puentes con el mismo nombre, tramo,
  PR, distancia, longitud y punto (San Blas, La Pereira, Tablaza, Puente Calle 128…), y 7 son
  copias exactas en todos los campos: un visor no podía distinguirlos ni deduplicar.
- Ahora `id_elemento` es el `:id` de la fila en datos.gov.co (cambia si el INVÍAS republica el
  conjunto), y el orden de la consulta termina en `:id`. Con un orden que repetía valores, dos
  páginas que siguen en la fuente (más de 3 000 puentes) podían cruzarse.
