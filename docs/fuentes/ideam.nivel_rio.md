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
