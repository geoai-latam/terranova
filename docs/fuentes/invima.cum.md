# INVIMA, Código Único de Medicamentos (`invima.cum_*`)

Cuatro conjuntos de datos.gov.co, uno por estado del registro sanitario. Los publica el INVIMA.
Licencia CC BY-SA 4.0. Se consultan en vivo.

| Fuente | Conjunto | Estado | Filas | Herramienta |
|---|---|---|---|---|
| `invima.cum_vigentes` | `i7cb-raxc` | vigente | 156 913 | `invima_medicamento_por_expediente`, `invima_medicamentos_por_principio_activo`, `invima_medicamentos_por_titular` |
| `invima.cum_renovacion` | `vgr4-gemg` | en trámite de renovación | 1 352 | `invima_medicamento_en_renovacion_por_expediente` |
| `invima.cum_otros_estados` | `spzp-dfuc` | otros estados | 114 423 | `invima_medicamento_otros_estados_por_expediente` |
| `invima.cum_vencidos` | `vwwf-4ftk` | vencido | 153 394 | `invima_medicamento_vencido_por_expediente` |

Las filas de vigentes se midieron el 2026-11-02; las demás vienen del perfil de cada ficha.

## Qué publica

Una fila por presentación comercial (CUM: expediente + consecutivo), por cada principio activo,
cada vía de administración y cada rol (fabricante, importador). Un producto con dos principios
activos y dos vías da cuatro filas por presentación: Buscapina Compositum ampollas (expediente
36344) tiene 28.

«Otros estados» mezcla, medido el 2026-11-02 en `estadoregistro`:

- pérdida de fuerza ejecutoria (52 238);
- temporalmente no comercializado (21 125);
- negado (19 218);
- cancelado (15 029);
- desistido (3 655);
- abandono (1 415);
- y otros menores (suspendido, revocado, solo exportación).

## Campos que importan

- **La dosis está en tres columnas:** `cantidad`, `unidadmedida` y `unidadreferencia`. En
  Buscapina, 2.5 g de dipirona por AMPOLLA DE 5 ML; en Motrin, 800 mg de ibuprofeno por TABLETA
  RECUBIERTA. La descripción que publica la fuente para `cantidad` dice «número de unidades en una
  presentación»: no es eso, es la cantidad del principio activo.
- **`concentracion` no es la dosis.** Es un código de letra (A-F y S; 117 210 filas son «A»), y no
  se encontró su tabla. La descripción de la fuente dice «10 mg/Tableta»: tampoco es eso.
- **Fechas:**
  - En vigentes, otros estados y renovación (`fechainactivo`), las fechas vienen en texto
    mes/día/año. Medido el 2026-11-02: ninguna empieza por un número mayor que 12, y hay muchas
    con el segundo número mayor que 12 (03/23/2012).
  - En vencidos, y en `fechavencimiento` de renovación, son fechas ISO.
- **Años de relleno en el vencimiento.** Medido en vigentes el 2026-11-02:
  - 110 171 filas no tienen fecha (Motrin no la tiene);
  - el año 3000 aparece 32 096 veces, en 11 fechas distintas (01/01, 12/31, 10/01…);
  - aparecen también 1000 (24), 1900 (634), 2050 (23), 2099 (54), 3001 (39), 3200 (6) y 9999 (8).

  Que el 3000 quiera decir «sin vencimiento» es una suposición: la fuente no lo dice.
- **Un CUM «Activo» puede traer `fechainactivo`.** En renovación, las presentaciones activas de
  Buscapina dicen inactivo desde 2020-06-01.

## Cobertura

Todos los registros de medicamentos del INVIMA, en los cuatro estados. Un expediente está en un
solo conjunto a la vez: la cetirizina de Tecnoquímicas (19994744) está en vigentes y no sale en
ninguno de los otros tres.

## Trampas medidas

1. **La dosis se perdía.** Las herramientas daban `concentracion: "A"` y `unidad_medida: "g"`, y
   no daban la cantidad: «dipirona A g» no es información (revisión de valor, 2026-10).
2. **Cuatro conjuntos para una pregunta.** Quien tiene el expediente no sabe en qué estado está, y
   el vacío de cada herramienta parecía un «no existe».
3. **Fechas en tres formas en la misma respuesta**, y años de relleno que parecen fechas.
4. **Muchas filas por producto, y CUM inactivos primero.** Medido el 2026-11-02:
   - 3 710 filas activas con acetaminofén son 276 productos;
   - de las 1 789 filas de metformina, 405 son de presentaciones inactivas (Glucophage uso
     institucional).
5. **La búsqueda es literal:**
   - «PARACETAMOL» da 26 productos y «acetaminofén», con tilde, 18. Sin tilde son 276; con el
     comodín de tildes, 289.
   - El INVIMA escribe ACETAMINOFEN, a veces con tilde, y a veces con el excipiente delante
     («361.11 MG DE ACETAMINOFEN DC 90. EQUIVALENTE A ACETAMINOFEN»).
   - Buscar también en `descripcionatc` (PARACETAMOL) se probó y no sirve: trae las filas de los
     otros principios de cada combinación (532 para paracetamol).

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `invima_medicamento_por_expediente` (v2) | medio → alto | con dosis |
| `invima_medicamentos_por_principio_activo` (v3) | medio → alto | un producto por fila, solo CUM activos, con dosis y presentaciones activas; busca con o sin tilde |
| `invima_medicamentos_por_titular` | medio | falta el principio activo; el titular se escribe de dos formas |
| `invima_medicamento_en_renovacion_por_expediente` (v2) | bajo → medio | con dosis y vacío que remite a los otros estados |
| `invima_medicamento_otros_estados_por_expediente` (v2) | bajo → medio | igual |
| `invima_medicamento_vencido_por_expediente` (v2) | bajo → medio | igual |

## Decisiones

- **2026-11-02, error 6 de la revisión de valor:**
  - La dosis sale en `dosis` («2.5 g por AMPOLLA DE 5 ML»), armada en la consulta SoQL con `||`,
    y también en `cantidad` y `unidad_referencia`. `concentracion` se queda, con su descripción
    corregida.
  - El motor suma `orden_fecha` (mda o dma, declarado por campo) y `anios_validos`. Las fechas
    salen en ISO, y un vencimiento fuera de 1950-2049 sale vacío, no como fecha.
  - El vacío de cada herramienta por expediente nombra las otras tres.
- **2026-11-02, patrón E (principio activo, v3):**
  - Se agrupa por producto y dosis, solo con CUM activos, con `presentaciones_activas` y
    `numero_productos` arriba. El orden es por nombre de producto y el tope, 500.
  - El motor suma `{marcador:sin_tildes}`, que cambia cada vocal con tilde por `_`, el comodín de
    una letra de LIKE.
  - El caso contrario (escribir sin tilde lo que la fuente tiene con tilde) no se cubre: con
    acetaminofén son 13 de 289 productos.
- **Pendiente:**
  - Una sola `invima_medicamento_estado_por_expediente` que mire los cuatro conjuntos. Pide
    consultas múltiples en el motor, igual que `cnmh_conflicto_municipio`.
  - Agrupar las vías en una lista.
