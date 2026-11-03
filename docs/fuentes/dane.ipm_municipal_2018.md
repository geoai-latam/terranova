# DANE: pobreza multidimensional municipal, censo 2018 (`dane.ipm_municipal_2018*`)

El anexo censal de pobreza municipal 2018 del DANE
(`anexo-censal-pobreza-municipal-2018.xlsx`). Términos del DANE: uso libre citando «Fuente: DANE».
Terrnova lo **copia** (ADR-0024): el DANE responde 403 al datacenter, así que la copia se baja desde
Colombia.

| Fuente | Hoja | Herramientas |
|---|---|---|
| `dane.ipm_municipal_2018` | «4_IPM Mpio dominios» | `dane_ipm_municipio` |
| `dane.ipm_municipal_2018_privaciones` | «6_Privaciones IPM Dpt-Mpio» | `dane_privaciones_municipio` |

## Qué publica

- La incidencia de la pobreza multidimensional de cada municipio en %: el total, las cabeceras y
  los centros poblados y el rural disperso.
- Las 15 privaciones de la medida, en % de hogares: analfabetismo, bajo logro educativo, trabajo
  informal, sin acceso a fuente de agua mejorada, etc.

Es una aproximación con el Censo Nacional de Población y Vivienda 2018. El DANE advierte que no se
compara con el IPM oficial, que sale de la encuesta y llega solo a departamentos
(`dane.ipm_departamental`).

## Campos que importan

- `ID`: el DIVIPOLA del municipio, que es por donde se consulta.
- `Municipio`: el nombre en mayúsculas.
- En las privaciones, `columna` es la privación y `valor` el porcentaje, tras pasar la tabla ancha a
  larga.
- **El año no viene en la tabla.** Todo es de 2018.

## Cobertura

1 122 municipios, una sola foto, de 2018. El DANE no ha publicado otra medida municipal.

## Trampas medidas

1. **Sin año, se lee como de hoy.** «El 77 % de Bojayá es pobre» es de 2018. La v1 no lo decía.
2. **Las privaciones salían en el orden del anexo,** casi alfabético. A «¿en qué está más mal?» hay
   que leer las 15 filas. Medido en producción el 2026-11-02: en Bojayá, trabajo informal 95,9 %,
   sin agua mejorada 78,3 % y bajo logro educativo 75,3 %. En Chía, trabajo informal 69,6 %.
3. **Las tildes:** el perfil de 2026-10-22 las vio dañadas («CHÍA» con un carácter de reemplazo). La
   copia de 2026-10-28 las trae bien (`CHÍA`, `BOJAYÁ`).

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `dane_ipm_municipio` | medio → alto | v2: `anio` 2018 y un aviso de que no se compara con el IPM oficial |
| `dane_privaciones_municipio` | medio → alto | v2: de la peor privación a la mejor, `peor_privacion` arriba, `anio` 2018 |

## Decisiones

- **2026-11-02, patrón E de la revisión de valor:**
  - El motor suma el derivado `fijo` (un `valor` igual para toda la fuente). Aquí da `anio: 2018`
    en cada fila. Es más fuerte que un aviso, porque el número va pegado al dato.
  - Las privaciones se ordenan por porcentaje descendente (`order: ["-valor", _fila]`).
