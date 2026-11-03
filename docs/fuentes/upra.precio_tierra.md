# UPRA: precio comercial de la tierra rural (`upra.rango_precios_nacional`, `upra.precio_tierra_rural`)

Dos publicaciones del mismo estudio de la Unidad de Planificación Rural Agropecuaria, con licencia CC
BY-SA 4.0.

| Fuente | Dónde | Modo | Herramientas |
|---|---|---|---|
| `upra.rango_precios_nacional` | capa 0 del MapServer `rango_precios_nacional` | copia | `upra_precio_tierra_en_punto`, `upra_rangos_precio_municipio` |
| `upra.precio_tierra_rural` | datos.gov.co `rttb-pk7n` | en vivo | `upra_precio_tierra_rural_municipio` |

## Qué publica

Zonas de precio homogéneo de la tierra rural agropecuaria. Cada zona tiene un rango de precio en
texto («Mayor que 60 - hasta 70»), su código, la categoría para el mercado de tierras y su área.

- **La capa nacional:** 178 973 zonas en 18 departamentos, con el año del estudio (`vigencia`).
- **datos.gov.co:** 244 municipios de 13 departamentos, sin año, con datos del 2022-06-16.

## Campos que importan

- `rango_precios`: texto **en millones de pesos por hectárea del año del estudio**. La unidad la
  dice la descripción de la capa, no el campo.
- `cod_precios`: los códigos E-… (zonas urbanas, resguardos) son exclusiones, no precios.
- `vigencia`: el año del estudio. Cambia por departamento: Cundinamarca 2016 y 2022, Boyacá 2015 y
  2021, Bolívar 2023.

## Cobertura

- 18 de 32 departamentos tienen estudio; los otros 14 no.
- Dentro de un departamento con estudio, lo que queda fuera del mercado de tierras no está. Chía
  no está, y Tunja tampoco (medido el 2026-11-02).
- La vigencia más reciente de toda la capa es 2023.

## Trampas medidas

1. **El año de la fuente no es el del dato.** El aviso general de la puerta decía «los datos llegan
   hasta 2023», y Cota contestaba con vigencia 2016: parecía que se contradecían. Ahora el aviso
   dice que la fuente no tiene nada posterior a 2023 y que el año de cada dato es el que trae la
   respuesta. La herramienta avisa además que el precio es del año del estudio.
2. **Vacío sin explicación.** Tunja y Chía daban `no_encontrado` a secas. Ahora el aviso dice por
   qué puede faltar y que eso no significa que la tierra no tenga precio.
3. **El rango «Mayor que 1000 »** trae un espacio al final, desde la fuente.
4. **La versión de datos.gov.co da un registro por polígono**: Cota, 116 polígonos sin agregar
   por rango.
5. **La versión de datos.gov.co escribe el mismo rango de dos formas.** «Mayor a 2 - hasta 3» y
   «Mayor que 2 - hasta 3» van con el mismo código. Las categorías salen como sigla o como nombre
   («CA» o «Cuerpo de Agua», «ZU» o «Zona Urbana»).
6. **Las dos versiones no tienen los mismos municipios.** Medido el 2026-11-03: de los 244 de
   datos.gov.co, uno no está en la capa nacional, Andes (Antioquia, 05034: 130 polígonos y
   25 068 ha). En Antioquia, la capa nacional tiene 15 municipios y datos.gov.co, 16.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `upra_precio_tierra_en_punto` (v4) | alto | aviso del año del estudio y del vacío; área con dos decimales |
| `upra_rangos_precio_municipio` (v4) | alto | igual; agrega hectáreas (dos decimales) y zonas por rango |
| `upra_precio_tierra_rural_municipio` (v2) | bajo → medio | agregada por rango, con unidad y categorías; para lo que la capa nacional no trae |

## Decisiones

- **2026-10-22:** la capa nacional va por copia, porque el servicio no responde al datacenter.
- **2026-11-02, patrón B de la revisión de valor:**
  - El motor cambia la redacción del aviso «Datos no recientes» para todas las fuentes: es el
    último año de la fuente, no el de la respuesta.
  - Las dos herramientas de la capa nacional avisan que el precio es del año del estudio, y la
    fuente avisa el vacío.
- **2026-11-03, patrón F:**
  - `upra_precio_tierra_rural_municipio` no se retira: Andes solo está en datos.gov.co.
  - Su v2 agrupa por código de rango y toma `max()` del nombre, para quedarse con la forma larga.
    Va del rango con más hectáreas al de menos, con `area_ha_total`, `poligonos_total` y
    `rango_con_mas_area`.
  - `categoria` traduce las siglas CA, ZU, NS y SI.
  - Un aviso da la unidad y que esta versión no trae el año. La descripción y el vacío remiten a
    `upra_rangos_precio_municipio`.
- **2026-11-03, revisión de valor (cierre):**
  - Revisado en producción que el aviso del año ya no contradice los datos. Casos: Cota, vigencia
    2016; Magangué (13430), vigencia 2023; Chía, vacío con su aviso.
  - Las hectáreas llegaban con 8 a 12 decimales (`53369.444637750035`). En la v4 de las dos
    herramientas de la capa nacional salen con dos.
