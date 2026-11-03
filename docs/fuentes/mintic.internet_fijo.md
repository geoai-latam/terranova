# MinTIC: accesos a internet fijo (`mintic.accesos_fijos_internet`, `mintic.internet_fijo_accesos`)

Dos conjuntos de datos.gov.co, uno detrás del otro. Ambos los publica el MinTIC (OficinaTI) con
licencia CC BY-SA 4.0. Se consultan en vivo.

| Fuente | Conjunto | Periodo | Herramientas |
|---|---|---|---|
| `mintic.accesos_fijos_internet` | `hwrp-3su3` | 2023-4T al último (hoy 2026-2T) | `mintic_internet_fijo_municipio` |
| `mintic.internet_fijo_accesos` | `n48w-gutb` | 2016 a 2023-3T | `mintic_internet_fijo_municipio_2016_2023` |

## Qué publican

Los accesos fijos a internet al cierre de cada trimestre, que reportan los proveedores. Vienen por
proveedor, municipio, segmento (residencial por estrato, corporativo, sin estratificar, uso propio
del operador), tecnología y velocidad. El conjunto nuevo sale de la Resolución 6333 de 2021 y añade
la velocidad de bajada y de subida en Mbps.

## Campos que importan

- **El año y el trimestre:** `anno` y `trimestre`. En el nuevo son números y en el viejo, texto.
- **El municipio:**
  - en el nuevo es `codigo_dane_municipio`, un número (5001 para Medellín), pero el filtro acepta
    `'05001'`;
  - en el viejo es `cod_municipio`, texto de 5 dígitos.
- **Los accesos:**
  - en el nuevo son `accesos_fijos_internet`, un número;
  - en el viejo son `no_de_accesos`, texto, así que se suma con `::number`.
- **La tecnología:** se publica con el nombre en inglés. «FIBER TO THE HOME (FTTH)» es fibra hasta el
  hogar y «HYBRID FIBER COAXIAL (HFC)», cable. El nuevo trae además «SATELITAL LEO».

## Cobertura

Medido el 2026-11-02:

- **El nuevo** tiene 2 072 381 filas, del cuarto trimestre de 2023 al segundo de 2026. Se actualizó
  el 2026-10-26.
- **El viejo** llega al tercer trimestre de 2023 y no cambia desde el 2024-02-23.

## Trampas medidas

1. **La herramienta se había quedado en 2023.** Mientras tanto, el MinTIC publicaba el conjunto
   nuevo, que nadie había descubierto. La v1 daba «fuera de cobertura» para 2025.
2. **2023 queda partido en dos.** Los trimestres 1 a 3 están en el viejo y el 4 en el nuevo. Chía
   empalma bien: 49 325 accesos en el 2023-3T (viejo) y 49 610 en el 2023-4T (nuevo).
3. **No había un total por trimestre.** Salían 10 tecnologías × 4 trimestres, y el total quedaba
   por sumar.
4. **La suma nacional pasa la del boletín trimestral del MinTIC:**
   - 2024-4T: 9 292 233 contra 9,09 millones;
   - 2025-2T: 9 731 621 contra 9,68 millones.

   No lo explican los segmentos «corporativo (accesos adicionales)» ni «uso propio interno del
   operador», que suman unos 23 000. Lo más probable son reportes corregidos después del boletín,
   pero no está verificado.
5. **La ficha de datos.gov.co declara frecuencia «Anual»,** pero los trimestres llegan uno a uno.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `mintic_internet_fijo_municipio` | medio → alto | v2: conjunto nuevo; total por trimestre y último trimestre arriba; el trimestre más reciente y la tecnología más grande primero |
| `mintic_internet_fijo_municipio_2016_2023` | medio | nueva: la serie vieja, con los mismos totales |

## Decisiones

- **2026-11-02, patrón E de la revisión de valor:**
  - `mintic_internet_fijo_municipio` pasa al conjunto nuevo, porque la pregunta normal es por lo
    reciente. La serie vieja queda en una herramienta aparte, con el periodo en el nombre.
  - El motor suma los avisos `cuando: fuera`. Cada herramienta, fuera de su rango de años, remite a
    la otra. Un aviso `encontrado` con `si: anio_consultado = 2023` dice que de 2023 solo está el
    cuarto trimestre.
  - Los nombres de tecnología quedan como los publica el MinTIC; la descripción del campo los
    traduce.
