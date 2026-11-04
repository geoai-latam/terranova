# SDP · estrato socioeconómico por manzana en Bogotá

La fuente es `sdp.estratificacion_manzana` y la herramienta, `sdp_estrato_en_punto`.

## Qué publica

- **Qué es:** la estratificación urbana que adopta la Secretaría Distrital de Planeación (Ley 142 de
  1994, art. 101). Hay una fila por manzana, con su estrato y el acto que lo fija.
- **Dónde está:** la capa 1 de `ordenamientoterritorial/estratificacion` en el ArcGIS de IDECA.
  IDECA no responde a la IP del datacenter, así que la copia se baja desde Colombia.
- **Licencia:** CC BY 4.0, según el portal de datos abiertos de Bogotá.

## Campos

| Capa | rt/1 | Nota |
|---|---|---|
| `CODIGO_MANZANA` | `manzana` | 8 dígitos (la UAECD usa 9: trampa 3) |
| `ESTRATO` | `estrato` | 1 a 6; 0 y 9, sin estrato (manzana no residencial); 7, sin información |
| `NORMATIVA`, `NUMERO_ACTO_ADMINISTRATIVO`, `FECHA_ACTO_ADMINISTRATIVO` | `normativa`, `numero_acto`, `fecha_acto` | el acto que fija el estrato |
| (derivado) | `estrato_nombre` | «estrato 4 (medio)» |

## Cobertura medida (copia del 2026-10-28)

- 45 051 manzanas urbanas de Bogotá.
- Por estrato:

  | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
  |---|---|---|---|---|---|---|
  | 5 882 | 7 025 | 15 736 | 12 052 | 2 438 | 1 038 | 880 |

- 45 044 manzanas las fija el Decreto 394 de 2017. Las otras 7 tienen cada una su resolución de
  2018, por reclamación.

## Trampas medidas

1. **Un punto en la calle no tiene manzana** (hallazgo #17 de GEO Copilot; 2026-11-03).
   - El punto (−74.05575, 4.6486) en Chapinero cae en la vía, a 6,6 m de la manzana más cercana, y
     da «no encontrado».
   - 15 m al occidente, (−74.0559, 4.6486), da la manzana 00820421, estrato 4.
   - Una dirección geocodificada suele caer en el eje de la vía.
2. **Es el estrato de la manzana, no el del predio.** Un predio puede tener otro por reclamación,
   y las manzanas no residenciales salen sin estrato.
3. **El código de manzana no es el de la UAECD.** La SDP da 8 dígitos (00820421) y el valor de
   referencia de la UAECD, 9 (008204021), para la misma manzana.

## Decisiones

- **v2, 2026-11-03.** Un aviso de vacío dice que las manzanas no cubren las calles: si es una
  dirección, hay que mover el punto hacia dentro del predio. También dice que «no encontrado» no
  dice nada del estrato de la zona.
- **Pendiente (B5, #17a):** proponer la manzana más cercana a 30 m o menos, con la distancia, en vez
  de solo avisar. Es un cambio del motor que sirve igual a la UAECD.

## Revisión de valor (2026-11-04)

- **Probado en producción:** el canario (Chapinero, estrato 4), la Plaza de Bolívar y una manzana
  de unas 100 ha en Ciudad Bolívar (−74,1655, 4,5605), las dos con estrato 0, y dos puntos en la
  vía (vacío, con su aviso).
- **Hallazgo:** el estrato 0 («sin estrato») es una manzana sin vivienda, pero la respuesta no lo
  decía, y se podía leer como un estrato bajo o un dato perdido. Ahora lleva un aviso cuando el
  estrato es 0 o 9.
