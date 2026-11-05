# Superfinanciera: entidades vigiladas (`superfinanciera.vigiladas`)

Un conjunto de datos.gov.co, publicado por la Superintendencia Financiera con licencia CC BY-SA 4.0.
Se consulta en vivo.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `superfinanciera.vigiladas` | `sr9n-792w` | `superfinanciera_vigiladas_buscar`, `superfinanciera_vigilada_por_nit` |

## Qué publica

El directorio de las entidades vigiladas: bancos, corporaciones financieras, fiduciarias,
aseguradoras, comisionistas, pensiones y filiales del exterior. Cada una trae el tipo y el código de
entidad, la razón social, la ciudad, la dirección, el NIT con el dígito y la página web.

## Campos que importan

- `tipo_entidad`: un número. **La tabla de nombres no está en este conjunto.** La SFC la publica en
  el CUIF (`mxk5-ce6w`, columna `nombre_tipo_entidad`), con los nombres abreviados y a veces
  cortados: «COMPANIAS DE FINANCIAMIENTO COMERCI», «CORPORACIONES FINA11NCIERAS». En el catálogo van
  completos y salen al lado del código (`tipo_entidad_significado`).
- `numeroidentificacion`: el NIT con el dígito de verificación pegado (8909039388 = 890903938-8).
  Las filiales del exterior traen «0».
- `uripaginaweb` y `direccion`: «Pendiente» cuando la entidad no los reportó.
- `razon_social`: trae la cláusula legal entera («…podrá girar también con la denominación…»).

## Cobertura

Medido el 2026-11-02, por tipo: 507 (51 entidades), 11 (38), 20 (37), 93 (33), 1 bancos (31),
5 fiduciarias (27), 111 (27)…

El CUIF del corte del 2026-08-31 nombra 26 tipos. **Trece tipos del directorio no tienen entidades
en el CUIF** y quedan sin nombre: 11, 20, 27, 93, 108, 111, 129, 142, 262, 507, 508, 510 y 600. No
se adivina el nombre por los ejemplos.

## Trampas medidas

1. **El tipo en código.** «NEQUI» daba `tipo_entidad: 4` y nada más. Ahora dice «Compañías de
   financiamiento».
2. **El banco salía de último.** El orden era por longitud de la razón social, y la del banco
   Bancolombia es la más larga por la cláusula legal. Ahora el orden es por tipo (1 son los bancos)
   y luego por longitud.
3. **Relleno como dato.** NIT «0» y página web «Pendiente» salían como si fueran valores. Ahora
   salen vacíos (`vacios` en la ficha).

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `superfinanciera_vigiladas_buscar` | medio → alto | tipo con nombre, banco primero, sin relleno |
| `superfinanciera_vigilada_por_nit` | medio → alto | tipo con nombre |

## Decisiones

- **2026-11-02, patrón C de la revisión de valor:**
  - `codigos` en `tipo_entidad`, tomados del CUIF de la propia SFC (`codigos_norma` dice de dónde).
  - El motor suma la opción `vacios`: textos que la fuente pone en lugar de un dato (también sirve
    para el patrón I).
- **Pendiente:** separar NIT y dígito como en el RUES, y buscar también por NIT sin dígito.

## Revisión de valor, 2026-11-05

- **La tilde está en el dato.** La razón social se escribe con tildes («BANCO DE BOGOTÁ S.A.»), y
  quien busca suele escribir sin ellas: «BOGOTA» daba «no encontrado» y «BOGOTÁ», 7. La búsqueda
  usa ahora `{nombre:vocales}`, que pone el comodín `_` en cada vocal de las palabras de 5 letras
  o más. «BANCO DE BOGOTA» da 5, «CORPORACION FINANCIERA» 8 y «FIDUCIARIA» las mismas 26.
- En palabras cortas el comodín casa con casi todo (`_` también es un espacio): «SURA» como `S_R_`
  daba 95, con «usar el» entre ellas. Por eso solo va en las de 5 letras o más.
- Un NIT que no es de una entidad vigilada (Ecopetrol) daba «no encontrado» sin aviso: el aviso
  manda a `rues_empresa_por_nit`.
