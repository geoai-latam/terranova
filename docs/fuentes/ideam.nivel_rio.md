# IDEAM: nivel de los ríos en las estaciones automáticas (`ideam.nivel_rio`)

Las lecturas de nivel de las estaciones hidrológicas automáticas del IDEAM, en datos.gov.co
(`bdmn-sqnh`), con licencia CC BY-SA 4.0. Se consultan en vivo y la consulta las agrega por día.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `ideam.nivel_rio` | `bdmn-sqnh` | `ideam_nivel_rio_diario_estacion` |

## Qué publica

Una fila por lectura, con:

- estación, municipio, departamento y zona hidrográfica;
- sensor (0230, «NIVEL INSTANTANEO»), unidad (`mt`), fecha y hora;
- valor.

En Bolombolo hay una lectura por hora (24 al día).

## Campos que importan

- `codigoestacion`: 10 dígitos con ceros a la izquierda («0026207080»).
- `valorobservado`: el nivel en metros **sobre el cero de la mira de esa estación**. No es la
  profundidad y no se compara entre estaciones: sirve para ver si el río sube o baja.
- La herramienta da por día el promedio, el mínimo y el máximo de cada sensor, y cuántas lecturas
  hubo.

## Cobertura

- Solo estaciones **automáticas**. Las convencionales no están, aunque estén activas: la
  limnimétrica de Leticia (río Amazonas) sale vacía (revisión de valor, 2026-11-02).
- Datos de hace un día: el 2026-11-03, la última lectura de Bolombolo era del 2026-11-01.

## Trampas medidas

1. **El promedio de la consulta trae 16 decimales** (3,0033333333333334 m). La mira se lee en
   centímetros: dos decimales bastan.
2. **Puede faltar un día entero.** Del 25 de octubre al 2 de noviembre de 2026, Bolombolo tiene 7 días
   con lecturas: falta el 25, y el 2 todavía no había llegado.
3. **El vacío no es «no hay río».** Una estación convencional, una suspendida y un código errado dan
   lo mismo. `ideam_estaciones_en_zona` dice la tecnología, el estado y la fecha de suspensión.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `ideam_nivel_rio_diario_estacion` | medio | v2: dos decimales, `dias_con_datos` y `ultimo_dia`; aviso de vacío que explica las convencionales |

## Decisiones

- **2026-11-03, revisión de valor:**
  - Promedio, mínimo y máximo con dos decimales.
  - Del resultado salen `dias_con_datos` (días distintos) y `ultimo_dia` (el último en el orden,
    que es por día).
  - El aviso de vacío dice que solo están las automáticas y remite a `ideam_estaciones_en_zona`.
- **Medido el 2026-11-03 en Bolombolo, río Cauca:**
  - el 27 de octubre, 3,52 m de promedio, con un máximo de 3,74: la creciente;
  - el 1 de noviembre, 3,28 m.
- **Pendiente: un complemento que corra con el resultado vacío** para decir la fecha de la última
  lectura de la estación (plan de producto, B5). Hoy el motor solo une el complemento cuando hay
  datos.

## Revisión de valor (2026-11-04)

- Probado en producción:
  - Bolombolo (canario): 3,00 m.
  - Universidad de la Sabana (2120700146, río Bogotá en Chía), 28-10 a 03-11: el máximo diario
    es **4,1 m en seis de siete días**, con un promedio de ~2,2 m.
  - Puente La Balsa (automática y activa en el catálogo): sin lecturas desde septiembre en la
    fuente. El vacío es honesto.
- En la fuente (una petición): las lecturas saltan de 2,0 a 4,1 m en una hora y vuelven
  (29-10, a las 00, 01, 02, 08, 09 y 13 h). Es un valor del sensor, no una creciente. Sube el
  máximo y también el promedio (2,74 m contra 2,49 m de mediana).
- La descripción del conjunto en datos.gov.co lo dice: los datos «no han sido validados por el
  IDEAM», son crudos, pueden estar «por fuera de los límites considerados normales» y no sirven
  como evidencia jurídica. Nada de eso llegaba a la respuesta.
- Arreglo:
  - `mediana_m` (SoQL `median`, medido en la fuente: 2,995 en el canario);
  - un aviso con datos, que dice que son lecturas crudas y cómo reconocer un pico;
  - el mismo aviso en `ideam_lluvia_diaria_estacion` (s54a-sgyg trae la misma cláusula).
