# DANE: crecimiento del PIB trimestral (`dane.pib_crecimiento_trimestral`)

El anexo de producción a precios constantes de las cuentas nacionales trimestrales
(`anex-ProduccionConstantes-<trimestre>trim<año>.xlsx`, hoja «Cuadro 1»). Términos de dane.gov.co,
verificados el 2026-11-04 (ADR-0039): verde, con la cita textual «Fuente: Departamento
Administrativo Nacional de Estadística: www.dane.gov.co». Terrnova lo **copia** (ADR-0024): el DANE
responde 403 al servidor, y la copia se baja desde Colombia.

| Fuente | Origen | Herramientas |
|---|---|---|
| `dane.pib_crecimiento_trimestral` | anexo de producción constantes, tabla del crecimiento anual | `dane_pib_crecimiento_trimestral` |

## Qué publica

El crecimiento anual en % de cada trimestre frente al mismo trimestre del año anterior, desde 2006.
Va para el PIB, el valor agregado, los impuestos y las 12 agrupaciones de actividades (CIIU Rev. 4).
Son series encadenadas de volumen, base 2015, con datos originales (sin desestacionalizar).

## Campos que importan

- `Concepto`: la actividad. La herramienta filtra «Producto Interno Bruto».
- `columna` y `subcolumna`: el año y el trimestre (I a IV), tras pasar la tabla ancha a larga.
- **El año trae el estado de la cifra:** «2026pr» es preliminar y «2024p», provisional. El DANE las
  revisa en los anexos siguientes.
- `valor`: el crecimiento. Viene con 15 decimales.

## Cobertura

El anexo del II trimestre de 2026 salió el 18 de agosto, y la copia es del 2026-10-28. El III
trimestre sale a mediados de noviembre.

## Trampas medidas

1. **El Cuadro 1 apila varias tablas:** niveles, crecimiento anual, año corrido… La copia lee solo
   la del crecimiento anual, de la fila 45 a la 62.
2. **El anexo cambia de nombre cada trimestre.** El archivo se descubre en la página.
3. **15 decimales:** 3.523392637718743, y el DANE publica 3,5 %.
4. **«pr» y «p» sin explicar en la respuesta.** La descripción lo decía, pero un agente lee la
   respuesta, no la descripción.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `dane_pib_crecimiento_trimestral` | alto | v2: un decimal; arriba, el último trimestre y su crecimiento; aviso de cifras preliminares |

## Decisiones

- **2026-11-02, patrón E de la revisión de valor (decimales de sobra):**
  - `decimales: 1` en el valor, como el boletín.
  - `ultimo_anio`, `ultimo_trimestre` y `crecimiento_ultimo_trimestre_pct` van arriba: en el II de
    2026, 3,5 %.
  - Un aviso explica «pr» y «p», y que la comparación es con el mismo trimestre del año anterior.

## Revisión de valor (2026-11-04)

- El año sale en número y `cifra` dice si es preliminar («pr») o provisional («p»).
- Con N trimestres pedidos ya no sale el aviso «acote la búsqueda».
