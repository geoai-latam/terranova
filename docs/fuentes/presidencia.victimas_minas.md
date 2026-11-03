# Presidencia: víctimas de minas, Descontamina Colombia (`presidencia.victimas_minas`)

Son las víctimas de minas antipersonal (MAP) y munición sin explosionar (MUSE) que registra
Descontamina Colombia, de la Presidencia. Están en datos.gov.co (`yhxn-eqqw`), con licencia CC BY-SA
4.0, y se consultan en vivo.

## Qué publica

Una fila por víctima, con:

- municipio;
- año del evento;
- condición: «Civil» o «Fuerza pública»;
- resultado: «Herido» o «Muerto»;
- sexo.

De 1990 a 2023. La herramienta solo da conteos, nunca la fila de una persona (ADR-0014).

## Campos que importan

- **Columnas cruzadas:** el resultado viene en la columna `genero` y el sexo en `estado`. La ficha
  los renombra (`resultado`, `sexo`).
- `codigodanemunicipio` es numérico: Granada, Antioquia, es 5313, sin el cero.

## Cobertura

- 1990 a 2023.
- Medido el 2026-11-03: la ficha de datos.gov.co no cambia desde el 2024-01-19, aunque declara
  actualización trimestral.

## Trampas medidas

1. **Dos fuentes de minas que no cuadran.** Medido el 2026-10-23:

   | Municipio | Descontamina | CNMH (`cnmh_minas_municipio`) |
   |---|---|---|
   | Granada | 78 | 66 |
   | San Carlos | 173 | 115 |

   Son registros distintos. Descontamina cuenta las víctimas de MAP y MUSE, con fuerza pública. El
   CNMH usa su propia tipología del conflicto. Ninguna de las dos herramientas nombraba a la otra.
2. **Lo más viejo primero.** La serie arrancaba en los noventa. Lo útil arriba es el total, cuántos
   murieron y cuándo fue la última víctima.

Medido el 2026-11-03:

| Municipio | Víctimas | Muertas | Civiles | Última |
|---|---|---|---|---|
| Granada (05313) | 78 | 20 | 42 | 2011 |
| San Carlos (05649) | 173 | 17 | 77 | 2010 |
| Bogotá (11001) | 30 | 11 | 11 | 2014 |

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `presidencia_victimas_minas_municipio` | medio → alto | v2: del año más reciente al más viejo, con `total_muertos`, `total_civiles` y `ultimo_anio`; nombra la del CNMH y explica por qué no cuadran |

## Decisiones

- **2026-11-03, patrón F de la revisión de valor:** las dos fuentes se quedan, porque miden
  distinto. Cada descripción nombra la otra. La del CNMH ya lo hacía (`cnmh.sievcac.md`).
