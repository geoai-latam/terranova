# ANT, resguardos indígenas formalizados (`ant.resguardos_indigenas`)

La capa «Resguardo Indígena Formalizado» de la Agencia Nacional de Tierras, en un FeatureServer de
ArcGIS (capa 0, servicio `DatosAbiertos/Resguardo_Indigena_Formalizado`). Licencia CC BY-SA 4.0.
Se consulta en vivo, con la geometría simplificada: el polígono completo de un resguardo grande
tardaba más de 90 s.

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
| `ant_resguardos_en_punto` | medio | v2: el vacío avisa que la capa no está completa; la descripción dice los errores de códigos |

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
