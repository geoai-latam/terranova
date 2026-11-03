# UAECD · valor de referencia del m² de terreno por manzana en Bogotá

La fuente es `uaecd.valor_referencia` y la herramienta, `uaecd_valor_referencia_en_punto`.

## Qué publica

- El catastro distrital calcula cada año el valor de referencia del suelo por manzana: la mediana
  del valor comercial por m² de terreno (Acuerdo 004 de 2012; Decreto 583 de 2015).
- Está en la capa 0 de `catastro/valorreferencia`, en el ArcGIS de la UAECD. Hay una fila por manzana
  y año.
- La capa no responde a la IP del datacenter: la copia se baja desde Colombia.
- Licencia CC BY 4.0, según el portal de datos abiertos de Bogotá.

## Campos

| Capa | rt/1 | Nota |
|---|---|---|
| `MANCODIGO` | `manzana` | 9 dígitos (la SDP usa 8: 008204021 frente a 00820421) |
| `V_REF` | `valor_m2` | pesos por m² de terreno |
| `ANO` | `vigencia` | 1 de enero del año |
| (derivado) | `valor_m2_ultimo`, `vigencia_ultima` | el valor del año más reciente que tenga la manzana |

## Cobertura medida (copia del 2026-10-28)

- 44 276 manzanas en total; por año, de 41 584 a 43 958, de 2017 a 2026.
- 41 858 manzanas tienen valor de 2026. Unas 2 400 no lo tienen, y su último valor es de un año
  anterior.
- Mediana de la ciudad: $1 200 000/m² en 2017 y $2 590 000 en 2026.

## Trampas medidas

1. **Un punto en la calle no tiene manzana** (hallazgo #17 de GEO Copilot; 2026-11-03).
   - (−74.05575, 4.6486), en Chapinero, cae en la vía a unos 6 m de la manzana y da «no encontrado».
   - Unos metros adentro se encuentra la 008204021.
2. **No todas las manzanas tienen el año en curso.** `vigencia_ultima` dice de qué año es el último
   valor: no hay que suponer que es el de hoy.
3. **Es la mediana de la manzana, no el avalúo de un predio.**
4. **Saltos grandes de un año a otro.** La 008204021 pasó de $4 300 000 en 2025 a $5 800 000 en
   2026 (+35 %). Es lo que publica la UAECD: la serie entera va en la respuesta.

## Decisiones

- **v2, 2026-11-03.**
  - Un aviso de vacío dice que las manzanas no cubren las calles y que el punto debe ir dentro del
    predio.
  - `valor_m2_ultimo` y `vigencia_ultima` dan el dato que se pregunta casi siempre sin leer la
    serie. Lo medido: la 008204021 da $5 800 000 (2026) y la 004108032 da $3 500 000 (2026).
- **Pendiente (B5, #17a):** proponer la manzana más cercana, como en el estrato de la SDP.
