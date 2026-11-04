# IGAC, base catastral pública del gestor (`igac.catastro.*`)

La base catastral pública de los municipios donde el IGAC es el gestor catastral. Es un
FeatureServer de ArcGIS Online (`Base_Catastral_Publica_del_Gestor_IGAC_<MM>_<AAAA>`), con una
capa por elemento. Licencia CC BY-SA 4.0. Se consulta en vivo. Bogotá, Medellín, Cali y los demás
gestores no están.

| Fuente | Capa | Qué es |
|---|---|---|
| `igac.catastro.terreno` | 7 (urbano) y 14 (rural) | el polígono del terreno, con su código |
| `igac.catastro.registro1` | 17 (tabla) | dirección, destino económico y áreas del predio |
| `igac.catastro.registro2` | 18 (tabla) | zonas física y económica, uso, pisos y calificación de la construcción |
| `igac.catastro.construccion` | 3 y 12 | las construcciones |
| `igac.catastro.manzana`, `.sector`, `.vereda`, `.perimetro` | 5, 8 y 16, 15, 2 | divisiones catastrales |
| `igac.catastro.nomenclatura_vial`, `.nomenclatura_domiciliaria` | 0 y 10, 1 y 9 | vías y placas |

## El corte vigente

- El nombre cambia con cada corte. El catálogo apunta al de junio de 2026
  (`..._06_2026`, ítem creado el 2026-07-28, «a corte de 30 de junio»).
- El servidor también tiene `Base_Catastral_Publica_IGAC_de_octubre`, pero es el corte del 31 de
  octubre de **2025** (ítem creado el 2025-11-24): es más viejo, no más nuevo (medido el
  2026-11-03).
- Tiene las mismas capas, más las de lo informal (4, 6, 11, 13). R_TERRENO tiene 2 604 233
  terrenos allí y 2 616 256 en el de junio.

## Campos que importan

- `CODIGO` (terreno) y `NUMERO_PREDIAL` (registro): el número predial nacional de 30 dígitos.
  Los 5 primeros son el municipio.
- `DESTINO_ECONOMICO`: una letra, con su significado por la Res. IGAC 070 de 2011, art. 86 (A
  habitacional, G recreacional, …).
- `DIRECCION`: en lo rural suele ser el nombre del predio («KASTILO»).
- `AREA_TERRENO`, `AREA_CONSTRUIDA`: m², según el registro.
- Los registros no traen nombres de propietarios en los campos que pide Terrnova (ADR-0014).

## Trampas medidas

1. **El terreno solo trae códigos.** Lo que dice qué es el predio (destino, áreas, dirección)
   está en el registro, tabla 17.
2. **Terrenos sin registro.** Yopal tiene 5 terrenos urbanos y ninguna fila en el registro: su
   catastro no lo lleva el IGAC. Chía, en cambio, tiene 15 448 urbanos, 16 832 rurales y 66 936
   registros (2026-11-03).
3. **Lento a veces:** el predio de Yopal tardó 11,8 s la primera vez y 0,6 s la segunda.
4. **Perímetro urbano: `CODIGO_NOMBRE` tiene dominio y `TIPO_AVALUO` no.**
   - `CODIGO_NOMBRE` va de 8301 a 8328 (cabecera municipal, centro poblado, corregimiento…). Hay
     30 perímetros con 8307 y 14 con 8326.
   - El texto es el de la fuente, aunque no cuadre: Chía sale «Corregimiento» siendo cabecera, y
     El Crucito (23807) sale 8326, «Zona Urbana».
   - `TIPO_AVALUO` no tiene dominio publicado. Trae «01» (721 perímetros), «02» (325) y así hasta
     «43», además de valores de 7 dígitos y la palabra «URBANO». Su significado no se inventa.
5. **Vías: una vía en muchos tramos, con espacios de más.**
   - La capa de vías trae un tramo por fila. En el canario de Chía son 29 tramos de 19 vías.
   - El nombre viene con espacios de más («CARRERA 11 » en Chía, «CALLE  3» en Popayán). Sin
     normalizarlos, la misma vía contaba dos veces.
   - `municipio_codigo_capa` no siempre es el del municipio: en Chía dice 23175 (Chinú, Córdoba)
     y en Popayán dice bien 19001.
   - Yopal y Fusagasugá no tienen vías en la capa: su catastro no lo lleva el IGAC.
6. **Manzana y sector: solo códigos.**
   - `U_MANZANA` trae `CODIGO`, `BARRIO_CODIGO` y `CODIGO_ANTERIOR`. `U_SECTOR` y `R_SECTOR`
     traen solo `CODIGO`. No hay capa de barrios ni nombre de barrio en ninguna parte.
   - `Shape__Area` está en Web Mercator (3857): en Chía infla el área en 0,7 %, y a 12° de latitud
     en 4,5 %. No se publica como m².
   - El sector rural de Chía pesa 263 KB completo y 4 KB simplificado a ~55 m. El sector urbano,
     72 KB y 1 KB. La manzana, 4 KB completa (medido el 2026-11-03).

## Herramientas que la usan (revisadas)

| Herramienta | Valor | Estado |
|---|---|---|
| `igac_predio_por_codigo` | bajo → alto | terreno + registro: dirección, destino con significado, áreas |
| `igac_registro_predio` | alto | el registro por código, con hasta 5 filas |
| `igac_perimetro_urbano_en_punto` (v2) | medio | el tipo de centro poblado con su significado; el tipo de avalúo, sin inventarlo |
| `igac_vias_en_zona` (v2) | medio | vías distintas y tramos por vía; avisa el código de municipio de la capa |
| `igac_manzana_en_punto` (v2) | medio | polígono completo; avisa que no hay nombre de barrio y remite a `predio_en_punto` |
| `igac_sector_en_punto` (v2) | medio | polígono simplificado; remite a `predio_en_punto` |

## Decisiones

- **2026-11-03, revisión de valor (`igac_predio_por_codigo` v2):**
  - El motor admite un `complemento`, y su primera fila da los hechos. Aquí el complemento es el
    registro: `direccion`, `destino_economico` (con `destino_economico_significado`, tomado de
    los `codigos` de la fuente) y las áreas.
  - Sin fila en el registro, un aviso lo dice y remite al gestor del municipio.
  - Si el registro se cae, sale «No se pudo saber…» y no el aviso de «no lo trae». El motor no
    da un aviso que mire un hecho de un complemento que falló.
- **2026-11-03, perímetro urbano (`igac_perimetro_urbano_en_punto` v2):**
  - `CODIGO_NOMBRE` lleva sus `codigos` (8301–8328) con los nombres como los escribe el IGAC, y la
    respuesta da `_significado`.
  - `TIPO_AVALUO` dice que no tiene dominio publicado.
- **2026-11-03, vías (`igac_vias_en_zona` v2):**
  - `vias` cuenta las vías distintas y `tramos_por_via` dice cuántos tramos tiene cada una. El
    motor quita los espacios de más al contar (`conteo_por` y `distintos`).
  - Un aviso dice que `municipio_codigo_capa` es el que trae la capa y puede no ser el del
    municipio.
- **2026-11-03, manzana y sector (v2):**
  - La revisión decía «solo códigos». La fuente no publica más: los códigos son la llave, no la
    respuesta. La manzana avisa que `codigo_barrio` es un código y que no hay nombre de barrio. Las
    dos remiten a `predio_en_punto` para los datos del lote.
  - El polígono ya salía completo. El del sector pasa a simplificado.
  - No se descompone el código (zona, sector, comuna, barrio): el significado de los dígitos de
    zona no se midió en la fuente.
  - Medido en producción: la manzana de Chía y la de Tabio (25785, 0,8 s); el sector rural de Chía
    y el de Tabio (257850001). Zipaquirá sale `fuera_de_cobertura` porque su catastro lo lleva el
    municipio.

## Revisión de valor (2026-11-04)

- Probado en producción: manzana, perímetro, predio, sector y vereda en Chía urbano y rural, en
  Tunja y en un punto rural de Suesca. Todas contestan.
- **El municipio salía solo como código** («25772»). Ahora `municipio` trae el nombre (SUESCA),
  de la tabla DIVIPOLA del DANE (`catalogo/codigos/divipola_municipios.yaml`). Va en las seis
  herramientas de punto que lo sacan del prefijo del código.
- **La verificación de cobertura casi nunca llega.** Un vacío de esta base dice «no se pudo
  comprobar si el IGAC cubre el municipio», aun donde sí lo cubre.
  - Causa: la capa de gestores de mapas.igac.gov.co tarda ~15 s desde la VPS, y el tope es de
    5 s.
  - Propuesta: copiar esa capa desde Colombia.
- El perímetro de Chía dice `tipo_centro_poblado: Corregimiento`, cuando es la cabecera. Es un
  error de la fuente y se deja como lo publica.
- **Zona geoeconómica.**
  - La descripción decía que el valor es catastral y no de mercado, y que la vigencia puede
    venir vacía o vieja, pero la respuesta no lo decía. Chía rural da $7 000 millones por
    hectárea sin vigencia; Calarcá, $480 000 por hectárea de 2014.
  - Ahora la respuesta lleva un aviso con datos.
## Revisión de valor del SINIC (2026-11-04)

- **Probado en producción:** Bogotá (el canario: PH matriz, habitacional), Medellín (NPH, lote
  urbanizable de uso público), Cali (comercial) y Chía (vacío).
- **Hallazgo:** en Chía el vacío de `sinic_predio_en_punto` no decía que el predio está en la base
  del IGAC. Ahora el aviso remite a `igac_predio_en_punto` y a `predio_en_punto`, y recuerda que una
  vía no es terreno.
