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

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `upra_precio_tierra_en_punto` | medio → alto | aviso del año del estudio y del vacío |
| `upra_rangos_precio_municipio` | medio → alto | igual; agrega hectáreas y zonas por rango |
| `upra_precio_tierra_rural_municipio` | bajo | redundante con la anterior y sin agregar: a fundir o retirar (patrón F) |

## Decisiones

- **2026-10-22:** la capa nacional va por copia, porque el servicio no responde al datacenter.
- **2026-11-02, patrón B de la revisión de valor:**
  - El motor cambia la redacción del aviso «Datos no recientes» para todas las fuentes: es el
    último año de la fuente, no el de la respuesta.
  - Las dos herramientas de la capa nacional avisan que el precio es del año del estudio, y la
    fuente avisa el vacío.
