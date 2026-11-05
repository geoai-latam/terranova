# RUES: empresas y establecimientos (`confecamaras.rues`, `confecamaras.rues_establecimientos`)

Dos conjuntos de datos.gov.co, publicados por Confecámaras con licencia CC BY-SA 4.0. Se consultan
en vivo.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `confecamaras.rues` | `c82u-588k` | `rues_empresa_por_nit`, `rues_empresas_buscar` |
| `confecamaras.rues_establecimientos` | `nb3d-v3n7` | `rues_establecimientos_por_nit` |

## Qué publica

El registro mercantil de todas las cámaras de comercio: personas jurídicas y entidades sin ánimo de
lucro, con NIT, razón social, cámara, matrícula, organización jurídica, estado, fechas y actividad
económica (CIIU). Aparte, los establecimientos de comercio con su propietario.

Las personas naturales no salen ni se buscan por nombre (ADR-0014).

## Campos que importan

- `cod_ciiu_act_econ_pri` y `cod_ciiu_act_econ_sec`: el código CIIU de 4 dígitos, sin nombre. El
  nombre sale al lado (`ciiu_principal_significado`), tomado de la lista oficial del DANE
  (`catalogo/codigos/ciiu_rev4_ac.yaml`).
- Una misma entidad puede tener una matrícula por cámara.

## Cobertura del CIIU

Medido el 2026-11-02 sobre 9 429 647 filas de `c82u-588k`:

- **«9999» en 1 373 373 filas y vacío en 581 715.** «9999» no es una clase de la CIIU: es relleno y
  sale vacío.
- **Códigos viejos con letra** (G521102, H552100…), de la CIIU Rev. 3, en unas 1 000 variantes:
  quedan sin nombre.
- **Sin contar el relleno ni los vacíos, el 96 % de las filas tiene nombre.**

## Trampas medidas

1. **Rev. 4 o Rev. 5.** El DANE adoptó la CIIU Rev. 5 A.C. con la Resolución 992 de 2026 (6 de
   agosto), que deroga la Rev. 4. Algunos códigos cambiaron de significado: 4923 es «Transporte de
   carga por carretera» en la Rev. 4 y «Otro transporte terrestre de pasajeros» en la Rev. 5. **El
   RUES sigue en la Rev. 4:** 1 009 683 filas traen códigos que solo existen en ella, y 70 traen
   códigos que solo existen en la Rev. 5. Ponerle nombres de la Rev. 5 habría inventado datos.
2. **El RUES mezcla ediciones de la Rev. 4.** Trae 3210 (actualización 2021) y 1030 (2020), que la
   de 2022 ya partió en clases nuevas. La lista junta las tres actualizaciones, y manda el texto de
   la más reciente. Medido: ninguna actualización le cambió el significado a un código que siguió
   existiendo. 7110 no está en ninguna de las tres (el DANE lo partió antes) y queda sin nombre.
3. **Los establecimientos de Ecopetrol** salen con CIIU 4719 (comercio al por menor): así los
   registra la cámara.
4. **«ACTIVA» no es «opera».** Medido el 2026-11-05:
   - PEHER CONSTRUIR LTDA EN LIQUIDACION (NIT 900000000, Facatativá) sale «ACTIVA» y sin
     renovar desde 2013;
   - LA PANADERIA LTDA. (Cartagena) sale «ACTIVA», sin renovar desde 1999 y sin NIT.

   Las sociedades que no renuevan en cinco años quedan disueltas y en liquidación (Ley 1727 de
   2014, art. 31). La respuesta lo avisa y manda a `ultimo_ano_renovado`.
5. **Un NIT, varias entidades.** El 900000000 (dígito 5) está en dos matrículas de entidades
   distintas, una de Facatativá y otra del Huila. Sale como lo registran las cámaras.
6. **Hay estados fuera de ACTIVA y CANCELADA**, como «SIN ESTADO» (RECOPETROL CARTAGENA LTDA).

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `rues_empresa_por_nit` | alto | CIIU con nombre (v3) |
| `rues_empresas_buscar` | alto | igual |
| `rues_establecimientos_por_nit` | alto | igual |

## Decisiones

- **2026-11-02, patrón C de la revisión de valor:**
  - El catálogo suma listas de códigos compartidas (`catalogo/codigos/`): una tabla oficial larga
    se escribe una vez y la usan varias fuentes con `codigos_lista`.
  - La de la CIIU la arma `scripts/codigos_ciiu.py` desde los tres Excel del DANE. Dice su norma.
  - «9999» sale vacío (`vacios`).
- **2026-11-03, patrón I:**
  - Las fechas del RUES (matrícula, renovación, cancelación) declaran `anios_validos: [1800, 2100]`:
    «0000-00-00» sale vacía, no como fecha.
  - Medido: Alpina Productos Alimenticios S.A. en Cali tiene `fecha_matricula` «0000-00-00» y
    categoría «PERSONA NATURAL» en una sociedad. La categoría se deja como la publica la fuente.
- **Cuando el RUES pase a la Rev. 5:** volver a medir qué códigos trae y cambiar de lista. No se
  mezclan las dos.
- **2026-11-05, revisión de valor:** aviso de que «ACTIVA» no es «opera» (renovación y Ley 1727 de
  2014) en `rues_empresa_por_nit` y `rues_empresas_buscar`, y aviso de un NIT en varias matrículas.
