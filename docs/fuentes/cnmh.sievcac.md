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

- Todo el país, hasta 2026 en la mayoría de los conjuntos (el primer año, sin medir; Granada tiene
  casos desde 1965). Ataques a poblados llega a 2023.
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
| `cnmh_dano_bienes_municipio` | bajo | casi siempre 0 víctimas; poca demanda |
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
- **Pendiente:**
  - Un código que no existe (99999) da «no encontrado» en las once y en la ficha, como cualquier
    municipio sin víctimas. La puerta no comprueba que el código DIVIPOLA exista.
  - Civiles frente a combatientes por modalidad: pide una consulta más por conjunto.
