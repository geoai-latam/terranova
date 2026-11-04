# IDEAM · alertas diarias por deslizamiento e incendios (OSPA)

Las fuentes son `ideam.alertas_deslizamiento` e `ideam.alertas_incendios`. Las herramientas son
`ideam_alertas_deslizamiento_municipio` e `ideam_alertas_incendios_municipio`.

## Qué publica

- La Oficina del Servicio de Pronósticos y Alertas del IDEAM publica cada noche (~23:30) un boletín
  con los municipios que tienen alerta ese día:
  - deslizamiento de tierra detonado por lluvia;
  - incendios de la cobertura vegetal.
- Los dos archivos son CSV separados por `;` en `bart.ideam.gov.co/ospa/DatosAbiertos/`. Acumulan
  el año en curso y se reinician cada 1 de enero.
- No hay API. En datos.gov.co (`m3en-ptx7`) la vista solo enlaza al archivo, y su `resource` da 403.
- `bart.ideam.gov.co` no responde al datacenter, así que la copia se baja desde Colombia con el
  refresco manual.
- Licencia CC BY-SA 4.0, según la ficha de datos.gov.co.

## Campos

| CSV | rt/1 | Nota |
|---|---|---|
| `COD_DANE` | `municipio_divipola` | 5 dígitos; la copia le pone el cero a la izquierda |
| `MUNICIPIO`, `DEPARTAMENTO`, `REGION` | igual | |
| `TEXTO_AMENAZA` | `nivel_alerta` | ALTA = roja, MODERADA = naranja, BAJA = amarilla |
| `ACUMULADO_TRES`, `ACUMULADO_DIEZ`, `DIAS_LLUVIA` | `lluvia_3_dias_mm`, `lluvia_10_dias_mm`, `dias_con_lluvia` | solo deslizamiento; a veces vacíos |
| `FECHA_EJECUCION` | `fecha` | el día del boletín |

## Cobertura medida (copia del 2026-11-02)

| | Filas | Boletines | Municipios con alguna alerta | En el último boletín (01-11) |
|---|---|---|---|---|
| Deslizamiento | 100 146 | 305 (01-01 a 01-11) | 939 | 464 (ALTA, MODERADA, BAJA) |
| Incendios | 44 085 | 305 | 1 046 | 18 (BAJA, MODERADA) |

## Trampas medidas

- **La última alerta no es una alerta vigente.** El boletín trae solo los municipios con alerta ese
  día. Un municipio que no está en el último boletín no tiene alerta hoy, aunque su última fila diga
  «ALTA».
  - GEO Copilot presentó como «vigente» la alerta de Chía del 2026-04-28 (hallazgo #11).
  - Bogotá (incendios) tuvo su última alerta el 2026-10-27, cuando el último boletín era el 01-11.
- **El último boletín es el de la copia, no el de hoy.** Si el refresco no se ha hecho, el boletín
  más reciente en la copia puede ser de hace días. Por eso `ultimo_boletin` es la fecha máxima de la
  copia, no la de hoy, y la respuesta dice de cuándo es la copia.
- **«No encontrado» es ninguna alerta en el año**, no «sin riesgo».
- **Medellín tiene 110 alertas en el año.** La herramienta trae las 15 más recientes y avisa
  «Vinieron 15 de 110» (#301).

## Decisiones

- **v2, 2026-11-03.** Lo agregado:
  - el complemento `ultimo_boletin`, la fecha máxima de `FECHA_EJECUCION` en toda la copia (de
    cualquier municipio);
  - `ultima_alerta`, la fecha de la primera fila, que es la más reciente;
  - `alerta_vigente` (derivado `igual`): verdadero si `ultima_alerta` = `ultimo_boletin`.
    - Sin la fecha del boletín no se afirma nada: el campo no sale.
    - Lo medido en producción: Abejorral (deslizamiento) y Cartagena (incendios) dan verdadero;
      Chía, Medellín y Bogotá dan falso.
- **El canario no fija `alerta_vigente`.** Cambia cada día; el canario pide `numero_registros ≥ 15`
  y los campos.
- **El derivado `igual` del motor** corre al final, con los agregados y los hechos del complemento
  ya en `datos`. Es genérico: compara dos campos que salen.

## Revisión de valor (2026-11-04)

- **Probado en producción:**
  - Deslizamiento:
    - Medellín: alerta vigente; 111 alertas en el año, la lista trae 15.
    - Chía: la última fue en abril, sin alerta vigente.
    - Barranquilla: vacío.
  - Incendio:
    - Puerto Gaitán: la última fue en agosto.
    - Chía: vigente.
    - Leticia: la última fue el 29 de octubre.
- **Hallazgo:** el vacío (ninguna alerta en el año) volvía `no_encontrado` sin aviso. Ahora el
  aviso dice que el IDEAM solo publica los municipios con alerta, y que no haber tenido alertas no
  es no tener amenaza.
- **Pendiente:**
  - El aviso genérico de lista corta («Acote la búsqueda») no aplica aquí, porque la entrada es
    solo el municipio.
  - Un conteo por nivel en el año daría más que las 15 últimas.
