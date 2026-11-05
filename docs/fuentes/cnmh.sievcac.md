# CNMH, SIEVCAC: víctimas del conflicto por modalidad (`cnmh.sievcac_*`)

Once conjuntos de datos.gov.co, uno por modalidad de violencia, del Observatorio de Memoria y
Conflicto del Centro Nacional de Memoria Histórica. Licencia CC BY-SA 4.0, verificada el
2026-10-23. Se consultan en vivo. El CNMH los actualiza cada semestre.

Tienen la misma forma, así que comparten este archivo:

| Fuente | Conjunto | Herramienta |
|---|---|---|
| `cnmh.sievcac_acciones_belicas` | `chb6-bfmq` | `cnmh_acciones_belicas_municipio` |
| `cnmh.sievcac_asesinatos_selectivos` | `djr9-7s3i` | `cnmh_asesinatos_selectivos_municipio` |
| `cnmh.sievcac_ataques_poblados` | `g3r2-mc68` | `cnmh_ataques_poblados_municipio` |
| `cnmh.sievcac_atentados` | `4jfs-zi6u` | `cnmh_atentados_municipio` |
| `cnmh.sievcac_dano_bienes` | `a2ga-ur2i` | `cnmh_dano_bienes_municipio` |
| `cnmh.sievcac_desaparicion_forzada` | `c59y-p4sz` | `cnmh_desaparicion_forzada_municipio` |
| `cnmh.sievcac_masacres` | `cj8q-zu3u` | `cnmh_masacres_municipio` |
| `cnmh.sievcac_minas` | `52eu-ic7d` | `cnmh_minas_municipio` |
| `cnmh.sievcac_reclutamiento` | `fc55-h9nc` | `cnmh_reclutamiento_municipio` |
| `cnmh.sievcac_secuestro` | `sg55-sszm` | `cnmh_secuestro_municipio` |
| `cnmh.sievcac_violencia_sexual` | `gtg9-672t` | `cnmh_violencia_sexual_municipio` |


## Qué publica

Una fila por víctima en un caso: municipio (DIVIPOLA), año, mes y día del hecho, sexo, etnia,
ocupación, edad, calidad de la víctima (civil o combatiente), coordenadas y un id anónimo de
persona y de caso. Terrnova solo sirve conteos por municipio y año: víctimas distintas
(`id_persona`) y casos distintos (`id_caso`). El resto queda fuera de la lista blanca (ADR-0014).

## Campos que importan

- `a_o`: el año del hecho. **El año 0 es «sin información»**, no un año.
- `id_persona`: unas pocas víctimas se repiten en dos filas, por eso se cuentan personas distintas.
- `fuerza_o_grupo_armado`: **no es el responsable**. Es la fuerza o el grupo de la víctima cuando
  era combatiente, y está vacío en las civiles. No se sirve. Los conjuntos no traen el presunto
  responsable: verificado en las columnas de asesinatos selectivos (2026-10-23).

## Cobertura

- Todo el país (el primer año, sin medir; Granada tiene casos desde 1965). El hecho más reciente
  de cada conjunto, en todo el país (medido el 2026-11-05):

  | Conjunto | Hasta |
  |---|---|
  | asesinatos selectivos | febrero de 2026 |
  | acciones bélicas, masacres, minas, secuestro | enero de 2026 |
  | daño a bienes, reclutamiento | diciembre de 2025 |
  | atentados | noviembre de 2025 |
  | desaparición forzada | septiembre de 2025 |
  | violencia sexual | julio de 2025 |
  | ataques a poblados | agosto de 2023 |

  Asesinatos selectivos se actualizó en julio de 2026 (`rowsUpdatedAt`) y trae 5 víctimas en 2026
  en todo el país, frente a 345 en 2025 y 452 en 2024.
- El CNMH revisa casos viejos con cada corte: las cifras pasadas pueden cambiar. Los canarios usan
  mínimos, no igualdades, para los totales.

## Trampas medidas

1. **Las modalidades son excluyentes.** Cada víctima cuenta en una sola, según la tipología del
   CNMH. Medido el 2026-11-02 en Bojayá (27099):
   - masacres tiene solo 2010 (11 víctimas, 1 caso);
   - acciones bélicas tiene 89 víctimas en 2002, en 3 casos. El caso 17896, del 2 de mayo, tiene
     81 víctimas, todas civiles: es la masacre de Bojayá (la pipeta en la iglesia), registrada como
     acción bélica porque ocurrió en un combate entre las FARC y las AUC.

   Un agente que pregunta «¿cuántas víctimas de masacres tuvo Bojayá?» recibe 11 y puede concluir
   que la masacre de 2002 no está. Pasa lo mismo con Toribío: las tomas de 2011-2014 no salen en
   ataques a poblados (la última es de 2005), porque el CNMH las registra como atentados o
   acciones bélicas.
2. **En reclutamiento, la mayoría no tiene año.** Medido el 2026-11-02 en `fc55-h9nc`: 11 484
   víctimas distintas con año 0 frente a 6 903 con año. Granada (05313): 29 de 43. Toribío
   (19821): 23 de 74. La serie por año, leída sola, se queda muy corta.
3. **Dos fuentes de minas que no cuadran.** `cnmh_minas_municipio` y
   `presidencia_victimas_minas_municipio` (Descontamina Colombia) cuentan lo mismo con criterios
   distintos: Granada 66 frente a 78; San Carlos 115 frente a 173 (2026-10-23).
4. **Lentas.** Acciones bélicas tarda 7-8 s y minas, cerca de 10 s, en producción.
5. **Daño a bienes solo trae los daños con víctimas.** El conjunto tiene una fila por víctima: en
   todo el país son 466 filas, 466 personas y 224 casos, y ninguna fila sin persona (medido el
   2026-11-03 en `a2ga-ur2i`). Un daño a bienes sin víctimas no está: Toribío sale con 1 caso, de
   2014.

6. **El último año está casi vacío.** El corte llega a 2026 solo por uno o dos meses (tabla de
   arriba). Un municipio sin filas en 2026 no quiere decir que no hubo víctimas ese año.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `cnmh_asesinatos_selectivos_municipio` | alto | la pregunta ya no promete «por grupo» |
| `cnmh_desaparicion_forzada_municipio` | alto | |
| `cnmh_secuestro_municipio` | alto | la pregunta ya no promete «por grupo» |
| `cnmh_acciones_belicas_municipio` | alto | aquí está Bojayá 2002 |
| `cnmh_atentados_municipio` | alto | |
| `cnmh_minas_municipio` | alto | avisa que hay otra fuente que no cuadra |
| `cnmh_violencia_sexual_municipio` | alto | |
| `cnmh_masacres_municipio` | medio | avisa que las modalidades son excluyentes |
| `cnmh_ataques_poblados_municipio` | medio | mismo aviso |
| `cnmh_reclutamiento_municipio` (v2) | medio | `victimas_sin_anio` y aviso del año 0 |
| `cnmh_dano_bienes_municipio` (v2) | bajo → medio | avisa que solo trae los daños con víctimas |
| `cnmh_conflicto_municipio` (compuesta) | alto | las once modalidades en una: total, resumen por modalidad y años pico |

## Decisiones

- **2026-11-02, error 5 de la revisión de valor:**
  - Las once herramientas avisan, cuando encuentran, que las modalidades son excluyentes, con el
    caso de Bojayá. La descripción también lo dice.
  - Cada fuente tiene un aviso de vacío: «no registra» en esta modalidad no quiere decir que no
    hubo violencia.
  - Asesinatos selectivos y secuestro dejan de prometer «por grupo»: la fuente no trae responsable.
  - Reclutamiento suma `victimas_sin_anio` (suma con `solo_si` año 0) y un aviso con la proporción
    nacional.
  - Minas nombra a `presidencia_victimas_minas_municipio` y dice que no cuadran.
- **2026-11-03, `cnmh_conflicto_municipio`:**
  - Es una ficha compuesta, como `ficha_empresa`, y no una herramienta del catálogo: corre las
    once en paralelo, con un tope de 20 s y de 20 créditos.
  - Por modalidad da víctimas, casos, víctimas sin año, primer y último año, y el año pico. No da
    la serie: para eso está cada herramienta.
  - Da el total y los cinco años con más víctimas, sumando las modalidades sin el año 0.
  - Los avisos que repiten las once partes (el de las excluyentes, el del homónimo y el de «no
    registra») salen una sola vez. Lo que dice una sola parte (minas, reclutamiento, ataques a
    poblados) va con su nombre.
  - Si una modalidad falla, la ficha sale `parcial` y avisa que el total es un mínimo.
  - Medido el 2026-11-03 (8 a 15 s):
    - Granada (05313): 1 252 víctimas; el pico es 2002, con 224.
    - Bojayá (27099): 315 víctimas; en 2002 son 113, y 89 de ellas están en acciones bélicas.
    - Toribío: 828 víctimas en las once modalidades. Las 131 víctimas de masacre de 1985 son
      Tacueyó.
- **2026-11-03, las sueltas remiten a la ficha (v2 de las once):**
  - El aviso de las excluyentes termina en `cnmh_conflicto_municipio`, que da el total en una
    respuesta, en vez de «hay que sumar las modalidades». El vacío de cada fuente también la nombra.
    La ficha recorta ese aviso por su final (`FIN_EXCLUYENTES`), que cambia con él.
  - Daño a bienes avisa que el conjunto solo trae los daños con víctimas, y su vacío lo repite.
  - Medido en producción: masacres en Bojayá (11, 2010) y Chía (vacío con la remisión); daño a
    bienes en Granada (2, 2003) y Toribío (1, 2014); la ficha de Toribío da el aviso de daño a
    bienes una vez, con su nombre.
- **2026-11-05, revisión de valor (v3 de las once):**
  - Cada una pregunta, en una consulta aparte (`complemento`), el año y el mes del hecho más
    reciente del conjunto en todo el país: `fuente_hasta_anio` y `fuente_hasta_mes`. Si el mes no
    es diciembre, un aviso dice que ese año puede estar incompleto. No se dice «el corte llega a»,
    porque en una modalidad rara (ataques a poblados) el último hecho puede ser anterior al corte.
  - La consulta usa `max(a_o * 100 + mes) - max(a_o) * 100` para tener el mes del último año en
    una sola fila, con `a_o >= 2020`: sin ese filtro recorre toda la tabla (4,4 s en ataques a
    poblados, frente a 0,4 s).
  - Suman `total_casos`, además de `total_victimas`: «¿cuántas masacres hubo en Granada?» se
    contesta con los casos (13), no con las víctimas (74). Medido en `cj8q-zu3u`: el conteo de
    casos distintos de todo el municipio da lo mismo que la suma por año.
  - Un código que no existe (99999) ya sale con el aviso de la puerta de que no figura en la lista
    de municipios.
- **Pendiente:**
  - Civiles frente a combatientes por modalidad: pide una consulta más por conjunto.
  - En `cnmh_conflicto_municipio`, el aviso del último año sale una vez, sin decir de qué
    modalidades es.
