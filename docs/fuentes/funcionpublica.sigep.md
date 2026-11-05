# Función Pública: servidores públicos del SIGEP (`funcionpublica.sigep_servidores`)

Un conjunto de datos.gov.co, publicado por el Departamento Administrativo de la Función Pública con
licencia CC BY-SA 4.0. Se consulta en vivo.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `funcionpublica.sigep_servidores` | `2jzx-383z` | `sigep_entidades_buscar`, `sigep_planta_por_entidad` |

## Qué publica

Una fila por servidor público con vinculación activa en el SIGEP: la entidad (código y nombre), el
orden (nacional o territorial), el nivel jerárquico del empleo, y datos de la persona (sexo,
nacimiento, salario, fecha de vinculación).

Terrnova solo saca agregados por entidad. Las columnas de persona no están en la lista blanca
(ADR-0014).

## Campos que importan

- `codigosigep`: texto con ceros a la izquierda («0346»). Medido el 2026-11-02: cada código tiene
  un solo nombre. Medido el 2026-11-05: 3 857 códigos de 4 dígitos y 27 de 5; «346» no da nada.
- `nombreentidad`: **en mayúsculas y sin tildes** («FISCALIA GENERAL DE LA NACION», «ALCALDIA DE
  CHIA»). La búsqueda le quita las tildes a lo que escribe la persona. La Ñ sí se conserva, pero
  no siempre: «GOBERNACION DE NARIÑO» y «CORPORACION AUTONOMA REGIONAL DE NARINO» (medido el
  2026-11-05).
- `niveljerarquicoempleo`: 27 valores, con tildes. Los más comunes son PROFESIONAL (85 272),
  ASISTENCIAL (75 006) y TÉCNICO (48 253). También hay niveles propios de la aviación civil o la
  docencia.

## Cobertura

Medido el 2026-11-02: la fuente se actualizó el 20 de octubre de 2026. Es una foto de la planta
activa, sin historia.

## Trampas medidas

1. **La entidad salía solo con su código.** `sigep_planta_por_entidad` pedía el código y devolvía
   los niveles sin decir de quién eran. No había forma de llegar de «Fiscalía» al 6194.
2. **No está todo el Estado.** La fuente dice que deja fuera la planta privada, el personal
   uniformado, los docentes y los trabajadores oficiales. Medido:
   - no están la Rama Judicial ni Ecopetrol;
   - el Ejército (8013, «EJERCITO NACIONAL DE COLOMBIA 1») sale con 4 308 servidores, solo los
     civiles;
   - **la descripción no se cumple del todo:** hay 12 962 filas DOCENTE y 10 220 TRABAJADOR OFICIAL.
3. **La Ñ va de dos formas.** Medido el 2026-11-05: «Nariño» daba 46 entidades (sin
   CORPONARIÑO, escrita «NARINO») y «Narino» daba solo esa.
4. **Tope de 50.** «Alcaldía» llena las 50 filas: las que faltan quedan sin decir.
5. **Código sin el cero.** «346» en la planta salía «no encontrado» sin explicación.
6. **Nombres con un número al final.** «EJERCITO NACIONAL DE COLOMBIA 1» y «DIRECCION GENERAL DE LA
   POLICIA NACIONAL 1» vienen así de la fuente.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `sigep_entidades_buscar` | alto | nombre → código, sin importar tildes ni la Ñ, con aviso si no encuentra o llega al tope |
| `sigep_planta_por_entidad` | alto | v2: con el nombre de la entidad y el total; el vacío explica el cero a la izquierda |

## Decisiones

- **2026-11-02, patrón C de la revisión de valor:**
  - Se suma la búsqueda por nombre, que agrupa por código, nombre y orden, con el nombre más corto
    primero. «Fiscalía» da solo la 6194; «Medellín» da 16 entidades.
  - La planta dice `nombre_entidad` y `total_servidores` (22 435 en la Fiscalía; 473 en la Alcaldía
    de Chía).
  - Si no encuentra, el aviso dice que el SIGEP no trae a todo el Estado. Así un «no encontrado» no
    se lee como «la entidad no existe».
- **2026-11-05, revisión de valor:**
  - La búsqueda cambia la Ñ por N a los dos lados: «Nariño» y «Narino» dan las mismas 47.
  - Con 50 resultados, un aviso dice que es el tope y que puede haber más.
  - El vacío de la planta dice que el código va con los ceros a la izquierda, como lo da la
    búsqueda.
