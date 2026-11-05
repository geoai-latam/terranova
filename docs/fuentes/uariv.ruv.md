# UARIV: Registro Único de Víctimas por municipio (`uariv.victimas_municipio`, `uariv.victimas_hecho_municipio`, `uariv.desplazamiento_anual`)

Tres conjuntos de datos.gov.co de la Unidad para las Víctimas, con licencia CC BY-SA 4.0. Se consultan
en vivo. Los tres acumulan un corte por mes: cada fin de mes se suma una foto nueva del registro.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `uariv.victimas_municipio` | `ykxr-xynr` | `uariv_victimas_municipio` |
| `uariv.victimas_hecho_municipio` | `9qih-4vkc` | `uariv_victimas_hecho_municipio` |
| `uariv.desplazamiento_anual` | `krnc-8azs` | `uariv_desplazamiento_municipio` |

## Qué publica

Sumas por municipio y corte, nunca personas: víctimas por ocurrencia (el hecho pasó allí), por
declaración, por ubicación y sujetos de atención, y eventos. Por hecho victimizante en `9qih-4vkc`;
por año del desplazamiento en `krnc-8azs`.

## Campos que importan

- `fecha_corte`: texto `DD/MM/AAAA`. Las herramientas piden por igualdad los cuatro últimos fines de
  mes y se quedan con el más reciente (spec 07).
- `param_hecho`: código del hecho; el texto del hecho cambia de codificación entre cortes, por eso
  se agrupa por el código.
- Las cuatro cifras de personas miden cosas distintas y no se suman. En el desglose por hecho, una
  persona con varios hechos cuenta en cada uno.

## Cobertura

Medido el 2026-11-05: el corte más reciente es el del 30/09/2026; el de octubre aún no está.

- Medellín (05001): 245 549 víctimas por ocurrencia, 783 837 por declaración, 451 163 por ubicación,
  392 116 sujetos de atención y 298 135 eventos; 16 hechos (desplazamiento, 146 138 por ocurrencia).
- Turbo (05837): 42 años de desplazamiento (1985 a 2026), 158 649 personas expulsadas; 2026 lleva
  290, hasta septiembre.
- San Andrés (88001): 221 víctimas por ocurrencia; 35 años con 127 personas expulsadas; 1986, 1987 y 1988, en
  cero.

## Trampas medidas

1. **El año en curso parecía completo.** La descripción de `uariv_desplazamiento_municipio` decía
   que el año en curso va incompleto, pero la respuesta no lo avisaba: 2026 salía con 290 personas
   en Turbo, como un año más.
2. **El vacío no explicaba nada.** Si un municipio no tiene filas en los cuatro últimos cortes, las
   tres herramientas salían «no encontrado» sin aviso. Si la UARIV deja de publicar cuatro meses, el
   vacío se leería como «cero víctimas».

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `uariv_victimas_municipio` | alto | las cuatro cifras del corte vigente; el vacío dice qué significa |
| `uariv_victimas_hecho_municipio` | alto | 16 hechos con nombre; el vacío dice qué significa |
| `uariv_desplazamiento_municipio` | alto | expulsión año por año; avisa que el último año llega hasta el corte |

## Decisiones

- **2026-11-05, revisión de valor:**
  - `uariv_desplazamiento_municipio` avisa siempre que el último año solo cuenta hasta
    `fecha_corte`.
  - Las tres explican el vacío: sin víctimas registradas, o la UARIV lleva cuatro meses sin publicar
    un corte.
