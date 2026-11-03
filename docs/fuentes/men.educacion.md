# MinEducación: educación preescolar, básica y media (`men.educacion_*`)

Tres conjuntos de datos.gov.co, publicados por el Ministerio de Educación con licencia CC BY-SA 4.0.
Se consultan en vivo.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `men.educacion_municipio` | `nudc-7mev` | `men_educacion_municipio` |
| `men.educacion_departamento` | `ji8i-4anb` | `men_educacion_departamento` |
| `men.educacion_etc` | `sras-4t5p` | `men_educacion_etc` |

## Qué publica

Por lugar y año, desde 2011: la población de 5 a 16 años, la tasa de matriculación, la cobertura
neta y bruta, la deserción, la aprobación, la reprobación y la repitencia, en porcentaje. Una ETC
es una entidad territorial certificada en educación: el departamento o un municipio certificado
(Medellín, 3759).

## Campos que importan

- El año es `a_o` en el de municipios y `ano` en los otros dos.
- El código: `c_digo_municipio` como texto, `c_digo_departamento` como número y `cod_etc` como
  texto.
- Los nombres a veces van sin tilde («Bojaya»).

## Cobertura

Medido el 2026-11-02: de 2011 a 2024. 2024 trae 1 122 municipios.

## Trampas medidas

1. **Lo más viejo primero.** La v1 ordenaba por año ascendente, y 2024 quedaba de último entre 14
   filas.
2. **Coberturas de más de 100 %.** En 2024, 94 de 1 122 municipios pasan de 100 % en la neta y 281 en
   la bruta: Chía, 107 % neta; Bojayá, 138 % bruta. No es un error. El denominador es la población
   proyectada por el DANE, en el municipio estudian niños que viven en otro, y la bruta cuenta a
   quienes están en un grado que no es el de su edad.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `men_educacion_municipio` | alto | v2: lo más reciente primero, resumen del último año, aviso de cobertura |
| `men_educacion_departamento` | alto | igual |
| `men_educacion_etc` | alto | igual |

## Decisiones

- **2026-11-02, patrón E de la revisión de valor:**
  - Orden por año descendente. Arriba van `ultimo_anio`, `cobertura_neta_ultimo_anio` y
    `desercion_ultimo_anio`.
  - Un aviso explica por qué la cobertura puede pasar de 100 %. Sale siempre que hay datos, porque
    el catálogo no puede condicionarlo a un número.
