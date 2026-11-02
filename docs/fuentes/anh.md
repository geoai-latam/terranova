# ANH: producción de crudo y gas, y regalías liquidadas (`anh.*`)

Tres conjuntos de datos.gov.co, publicados por la Agencia Nacional de Hidrocarburos con licencia
CC BY-SA 4.0. Se consultan en vivo.

| Fuente | Conjunto | Desde | Herramientas |
|---|---|---|---|
| `anh.produccion_crudo` | `fdvb-hsrf` | 2014 | `anh_crudo_campo`, `anh_crudo_municipio` |
| `anh.produccion_gas` | `5dux-bfvx` | 2014 | `anh_gas_campo`, `anh_gas_municipio` |
| `anh.regalias_liquidadas` | `j7js-yk74` | 2010 | `anh_regalias_campo`, `anh_regalias_municipio` |

## Qué publica

- **Producción fiscalizada:** una fila por campo, municipio, operadora, año y mes. Crudo en barriles
  y gas en kpc.
- **Regalías:** la liquidación definitiva por campo, contrato, tipo de hidrocarburo y mes, en pesos.
  El volumen va en barriles o en kpc según el hidrocarburo.

## Campos que importan

- `vigencia` / `a_o` y `mes`: numéricos. El orden por mes es numérico.
- `produccion_bls`, `produccionkpc`, `regaliascop`: texto con coma de miles. Se suman con
  `replace(…, ',', '')::number`.
- `volumenregaliablskpc` (regalías): **barriles si el hidrocarburo es petróleo (O) y kpc si es gas
  (G)**, en la misma columna. Se comprobó con el valor: en Boral 2025 el barril de regalía sale a unos
  $241 000 y el kpc de gas a unos $29 600.
- Un campo puede estar en dos municipios: Castilla está en Acacías y en Castilla Nueva (así lo escribe la fuente).

## Cobertura

Medido el 2026-11-02 en `fdvb-hsrf`, filas por mes en todo el país:

- en 2025, de 330 a 350 filas por mes, menos **noviembre, que trae 106**;
- **2026 llega a marzo.**

Castilla 2025 no tiene octubre ni noviembre: sus dos municipios saltan de septiembre a diciembre.
Las regalías de Puerto Gaitán en 2026 llegan a marzo.

## Trampas medidas

1. **El total del año suma los meses que hay.** Castilla 2025 da 16 932 680 barriles en 10 meses,
   y la v1 lo daba como si fuera el año entero.
2. **Ceros en gas:** la mitad de las líneas de gas está en 0 (2025: 3 314 de 6 459). Cusiana 2024
   trae a Aguazul en 0 los doce meses, y eso era la mitad de la respuesta. El crudo no tiene ceros
   (2025: ninguno en 3 834 líneas).
3. **Un campo entero en 0.** Agave tiene gas en la fuente en 2025, con 12 meses, todos en 0.
4. **Meses que faltan no siempre son hueco de la fuente.** El gas de Borbón empieza en julio de
   2025: son 6 meses porque el campo arrancó.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `anh_crudo_campo` | alto | da `meses_con_datos` y `hasta_mes`, con aviso si faltan |
| `anh_crudo_municipio` | alto | igual |
| `anh_gas_campo` | alto | v3: sin las líneas en 0 (`lineas_en_cero` las cuenta); los meses salen de la fuente entera |
| `anh_gas_municipio` | alto | igual |
| `anh_regalias_campo` | alto | igual, y `unidad_volumen` (barriles o kpc) |
| `anh_regalias_municipio` | alto | igual, más los meses por campo (`meses_liquidados`) y `unidad_volumen` |

## Decisiones

- **2026-11-02, error 9 de la revisión de valor:**
  - El motor suma el derivado de resultado `distintos`: cuántos valores distintos hay de un campo.
  - Las seis dan `meses_con_datos` (los meses distintos) y `hasta_mes`, y avisan cuando faltan
    meses. El aviso no afirma la causa: puede faltar la publicación o la producción.
  - Aquí no hace falta el corte de todo el país (el `complemento` de Policía): el hueco es de cada
    campo, y los meses del propio resultado lo muestran.
- **2026-11-02, patrones D y E de la revisión de valor:**
  - Las regalías dicen `unidad_volumen`, que sale del tipo de hidrocarburo.
  - El gas por campo no lista las líneas en 0 (`having`). Los meses y las líneas en 0 se cuentan
    en un complemento sobre todo el campo, así que un mes en 0 no se lee como un mes que falta.
  - Si todo el año está en 0, el vacío lo dice.
  - El aviso de meses que faltan suma la causa medida: el campo empezó o dejó de producir ese año.
