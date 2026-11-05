# ANT, resguardos indígenas formalizados (`ant.resguardos_indigenas`)

La capa «Resguardo Indígena Formalizado» de la Agencia Nacional de Tierras, en un FeatureServer de
ArcGIS (capa 0, servicio `DatosAbiertos/Resguardo_Indigena_Formalizado`). Licencia CC BY-SA 4.0.
Desde el 2026-11-05 se sirve de una copia de Terrnova en PostGIS con los polígonos completos, como
los publica la ANT (en vivo, el polígono completo de un resguardo grande tardaba más de 90 s y solo
se servía simplificado).

## Qué publica

Un polígono por resguardo, con:

- `NOMBRE` y `PUEBLO`;
- `DEPARTAMENTO` y `MUNICIPIO` (DIVIPOLA, con errores: ver abajo);
- el último acto administrativo (tipo, número y fecha);
- `AREA_TOTAL_ACTOS_ADMIN`: el área según los actos, en ha.

## Cobertura

989 resguardos en el país (medido el 2026-11-03). Los departamentos con más: Chocó (27), 122;
Putumayo (86), 111; Tolima (73), 110; Cauca (19), 87; Nariño (52), 72.

## Trampas medidas

1. **No están todos.** Toribío, Tacueyó y San Francisco, los grandes resguardos nasa de origen
   colonial en Toribío (Cauca, 19821), no aparecen: ni por punto, ni por nombre, ni por
   municipio (2026-11-03). Un punto en Toribío (-76,27; 2,95) da «no encontrado».
2. **Códigos que no son códigos.** Medido el 2026-11-03, de los 989:
   - 46 traen el nombre del municipio en vez del DIVIPOLA («NATAGAIMA», «PUERTO GAITÁN»);
   - 9 traen el nombre del departamento («PUTUMAYO», «CAQUETÁ»);
   - 13 traen un municipio de otro departamento (13473, de Bolívar, en dos resguardos del Cauca).
3. **Un resguardo, un municipio.** El de Vaupés (3,96 M ha) cruza varios municipios y da solo
   97001.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `ant_resguardos_en_punto` | medio | v4: sobre la copia; con `geometria`, el polígono completo |
| `ant_resguardos_en_poligono` | alto | v1: «¿este lote cae en un resguardo?», con las hectáreas dentro del lote |
| `ant_resguardos_en_zona` | medio | v1: por rectángulo, con el conteo por pueblo; para pintar la capa |
| `ant_resguardos_municipio` | medio | v1: los que la ANT anota en el municipio, con su aviso |

Probada en producción el 2026-11-03:

- Vaupés (canario): Resguardo Indígena Vaupés, Cubeo y 18 grupos más, Acuerdo 378 de 2024.
- Alta Guajira (-72,0; 11,7): Wayuu de la Alta y Media Guajira, Resolución 28 de 1994,
  1 067 505 ha.
- Toribío: «no encontrado», con el aviso.

## Decisiones

- **2026-11-03, revisión de valor (v2):**
  - El vacío lleva un aviso: la capa no está completa, faltan los resguardos de Toribío, y para
    una consulta previa hay que confirmar con el Ministerio del Interior.
  - Los códigos errados se dejan como los publica la ANT y la descripción los advierte.
- **Pendiente:** buscar una capa pública más completa (IGAC o Ministerio del Interior) sin inicio de
  sesión.

## Revisión de valor (2026-11-04)

- Probado en producción: Vaupés (canario), Sierra Nevada (Kogui - Malayo y Arhuaco, con la forma
  completa: un MultiPolygon de ~21 000 vértices) y Bogotá (vacío, con su aviso). Contesta bien.
- Los códigos DIVIPOLA salían solos («47», «47001»): un agente no sabe que es Magdalena, Santa
  Marta. Ahora `departamento_divipola_significado` y `municipio_divipola_significado` traen el
  nombre, de la tabla DIVIPOLA del DANE (`catalogo/codigos/divipola_*.yaml`, que arma
  `scripts/codigos_divipola.py`). Lo mismo en los consejos comunitarios.
- La ANT anota un solo municipio aunque el resguardo cruce varios (el Kogui cubre parte de
  Magdalena, La Guajira y Cesar y dice «47001»): la descripción del campo lo advierte.
- En la UAF (`ant_uaf_en_punto`) un punto fuera de los 286 municipios publicados salía «no
  encontrado» sin aviso. Ahora el vacío dice que la capa no cubre el punto, no que no haya UAF.

## Copia y herramientas por zona y municipio (2026-11-05)

- **Copia:** origen `arcgis`, capa 0, clave `OBJECTID`, 25 por página, índice en `MUNICIPIO`, sin
  `tolerancia`: los polígonos se guardan completos (son límites legales). Ingerida en producción el
  2026-11-05 (tabla `copia.ant_resguardos_indigenas_20261105155849656002`): 989 filas, 989
  geometrías, 1 659 809 vértices.
- **Fechas antes de 1970:** la más vieja es de 1956-10-18. En Windows,
  `datetime.fromtimestamp` falla con un epoch negativo; `copias._convertir` suma milisegundos a la
  época.
- **Una geometría inválida:** Sikuani de Awaliba (Puerto Gaitán, 50 024 vértices) tiene una
  autointersección y pasa del tope de reparación. Medido el 2026-11-05: el punto y el cruce con un
  polígono que la toca responden bien.
- **Nombre repetido:** 986 nombres distintos en 989 filas; la clave de la copia es `OBJECTID`.
- **Por municipio:** filtra por `MUNICIPIO`, el código que anota la ANT. Lo dicen la descripción y
  los avisos: uno solo por resguardo y 46 con el nombre en vez del código. Para lo que toca un
  municipio, la de zona o la de polígono.
- **Geometría fiel:** el cruce siempre usa la forma completa. La de polígono va de a 20 por página,
  y por eso `geometria` la devuelve entera (ADR-0032). La de zona y la de municipio van de a 1000,
  simplificadas a unos 55 m, con el aviso del motor.
- **Medido en la fuente el 2026-11-05** (returnCountOnly), igual en la copia:
  - Franja Silvia-Totoró (canario de polígono): 4, y 7 con su rectángulo.
  - Rectángulo [-77, 1, -76, 2]: 61.
  - `MUNICIPIO = 73217` (Coyaima): 34.
