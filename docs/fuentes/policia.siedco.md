# Policía Nacional, delitos denunciados (SIEDCO) (`policia.*`)

Siete conjuntos de datos.gov.co con los delitos que la Policía Nacional registra por denuncia.
Licencia CC BY-SA 4.0. Se consultan en vivo. Tienen la misma forma, así que comparten este archivo.

| Fuente | Conjunto | Herramienta |
|---|---|---|
| `policia.hurto_vehiculos` | `9vha-vh9n` | `policia_hurto_vehiculos_municipio` |
| `policia.hurto_comercio_residencias` | `6sqw-8cg5` | `policia_hurto_comercio_residencias_municipio` |
| `policia.homicidios_transito` | `ha6j-pa2r` | `policia_homicidios_transito_municipio` |
| `policia.lesiones` | `72sg-cybi` | `policia_lesiones_municipio` |
| `policia.abigeato_pirateria` | `d4fr-sbn2` | `policia_abigeato_pirateria_municipio` |
| `policia.delitos_sexuales` | `fpe5-yrmw` | `policia_delitos_sexuales_municipio` |
| `policia.violencia_intrafamiliar` | `vuyt-mqpw` | `policia_violencia_intrafamiliar_municipio` |

## Qué publica

Una fila por día, municipio, conducta (el artículo del Código Penal), arma, género y grupo de edad,
con `cantidad`. Son denuncias, no hechos: no todos los delitos se denuncian. Hurto de vehículos
tiene 656 635 filas en el país (2026-10-23).

## Campos que importan

- `fecha_hecho`: **texto dd/mm/aaaa**. El año se filtra con `like '%/aaaa'` y el mes es
  `substring(fecha_hecho, 4, 2)`.
- `codigo_dane`: el DIVIPOLA con tres ceros al final (25175000).
- `cantidad`: texto en algunos reportes, así que se suma con `cantidad::number`.
- `genero`: algunos registros no lo traen, y la fila sale sin la clave.

## Cobertura

- De 2010 al último corte publicado. **El año en curso está incompleto.** Medido el 2026-11-02:
  los siete conjuntos llegan a julio de 2026 (meses 01 a 07). La ficha se actualizó el 1 de
  septiembre de 2026.
- Un año pasado tiene los 12 meses (2025, medido en hurto de vehículos y lesiones).

## Trampas medidas

1. **El año a medias parece un año entero.** Medellín, hurto de vehículos: 2 955 casos en 2026
   (hasta julio) frente a 5 916 en todo 2025. Sin el corte, «el hurto bajó a la mitad»
   (2026-11-02).
2. **El corte es de la fuente, no del municipio.** Un municipio sin casos en julio no deja ver que
   la fuente llega a julio. Por eso el corte se mide en todo el país.
3. **Lesiones suma dolosas y culposas de tránsito** (art. 120): «7 286 lesiones» en Medellín 2025
   no son 7 286 riñas. Se distinguen por el tipo.
4. **Abigeato y piratería** junta tres delitos que no tienen que ver entre sí: robo de ganado
   (`HURTO ABIGEATO`), robo de carga en carretera (`HURTO PIRATERÍA TERRESTRE`) y hurto a
   entidades financieras (`HURTO ENTIDADES FINANCIERAS`). Su suma no es la cifra de ninguno. En el
   hurto a entidades financieras la víctima es la entidad y la fila no trae `genero`.
5. **Abigeato: las cifras recientes son mucho menores** que las de 2017, por la validación de
   denuncias con la Fiscalía que anuncia la ficha. En todo el país (medido el 2026-11-03):

   | Año | Abigeato | Piratería terrestre | Entidades financieras |
   |---|---|---|---|
   | 2017 | 5 135 | 443 | 163 |
   | 2022 | 2 551 | 186 | 138 |
   | 2024 | 1 223 | 163 | 64 |
   | 2025 | 813 | 101 | 43 |
   | 2026 (enero a julio) | 345 | 32 | 10 |

   Bogotá tiene la mayor piratería terrestre de 2025 (17 casos). Medellín 2025 tiene 2 abigeatos y
   ningún caso de los otros dos.
6. **Lentas:** la consulta del municipio tarda 6-7 s en la fuente (Chía 2024, hurto de vehículos,
   2026-11-02; Medellín 2025, abigeato, 14,7 s el 2026-11-03). La del corte del país tarda
   0,6-1,1 s.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `policia_hurto_vehiculos_municipio` | alto | dice hasta qué mes publica la fuente |
| `policia_hurto_comercio_residencias_municipio` | alto | igual |
| `policia_homicidios_transito_municipio` | alto | igual; las cifras de Medellín (505 en 2025) están por contrastar |
| `policia_lesiones_municipio` | alto | igual |
| `policia_delitos_sexuales_municipio` | alto | igual |
| `policia_violencia_intrafamiliar_municipio` | alto | igual |
| `policia_abigeato_pirateria_municipio` | medio | igual; `casos_por_tipo` separa los tres delitos |

## Decisiones

- **2026-11-02, error 9 de la revisión de valor:**
  - El motor suma la consulta `complemento`: va a la fuente a la vez que la principal, y su
    primera fila sale como hechos del resultado. No cuenta en el total, y si falla la respuesta
    lo avisa y sigue.
  - Las siete dan `fuente_hasta_mes` y `fuente_meses_publicados` del año pedido, medidos en todo
    el país.
  - Con menos de 12 meses, avisan que el año está incompleto y piden comparar los mismos meses.
- **2026-11-03, abigeato separado por delito (revisión de valor):**
  - `policia_abigeato_pirateria_municipio` v4 da `casos_por_tipo`: el total de cada delito. En
    Yopal 2025: 21 abigeatos y 1 hurto a entidad financiera.
  - La descripción dice que `total_casos` suma los tres y no es la cifra de ninguno.
  - El derivado `suma_por` con `tipo: int` da enteros (21, no 21.0).
  - No se partió en tres herramientas: la fuente los publica juntos, y una consulta da los tres.
- **Pendiente:**
  - `genero: "sin dato"` cuando la fuente no lo trae.
  - Homicidios dolosos: MinDefensa `m8fd-ahd9` (error 12).
