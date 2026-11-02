# MinDefensa: homicidios (`mindefensa.homicidios`)

Un conjunto de datos.gov.co, publicado por el Ministerio de Defensa Nacional con licencia CC BY-SA
4.0 (verificada el 2026-11-02 en los metadatos del conjunto). Se consulta en vivo.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `mindefensa.homicidios` | `m8fd-ahd9` | `mindefensa_homicidios_municipio` |

## Qué publica

«Toda muerte que fuere causada por otra persona por cualquier tipo de elemento», medida en
víctimas. Hay una fila por hecho, con fecha, municipio, zona, sexo de la víctima, arma o medio,
modalidad presunta, caracterización de la Fiscalía (SPOA) y `cantidad` de víctimas. No trae nombres
ni documentos.

Medido el 2026-11-02: 345 195 filas y 345 917 víctimas, del 1 de enero de 2003 al 30 de septiembre
de 2026. Se actualizó el 21 de octubre de 2026.

## Campos que importan

- `fecha_hecho`: una fecha de verdad, no texto como en la Policía. El año sale con `date_extract_y`.
- `cod_muni`: el DIVIPOLA de 5 dígitos, siempre (sin los tres ceros de la Policía).
- `cantidad`: es 1 en 344 604 filas y llega a 5. Se suma: contar filas da menos víctimas.
- `sexo`: MASCULINO, FEMENINO, NO REPORTA (125 filas) y SIN ESTABLECER (2).
- `spoa_caracterizacion`: «HOMICIDIO INTENCIONAL O CON DOLO» o «FEMINICIDIO» (1 919 filas).
- `_modalidad_presunta`: el nombre empieza con guion bajo. Sicariato, riñas, atraco, ataques de
  grupos armados…

## Cobertura

- De 2003 a 2025, cada año trae los doce meses.
- **2026 llega a septiembre** (10 432 víctimas).

## Verdades medidas

- Cali 2025: 1 068 víctimas, 999 hombres y 69 mujeres; 745 por sicariato y 879 con arma de fuego.
- Medellín 2025: 333 víctimas, 8 feminicidios.
- Sopó: ninguna en 2024 ni en 2025, y 2 en 2026.
- País 2025: 14 038 víctimas; 11 089 con arma de fuego.

## Trampas medidas

1. **El año en curso parece bajo.** Cali 2026 suma 847 en nueve meses.
2. **Feminicidio no es lo mismo que víctima mujer.** Cali 2025 tiene 69 mujeres y 5 feminicidios:
   la caracterización la da la Fiscalía, y la mayoría de las mujeres muertas están en sicariato y
   riñas.
3. **Un municipio sin filas no es un error.** Sopó 2024 no tiene homicidios en la fuente. La
   respuesta es `no_encontrado` con aviso, y un año fuera de 2003-2026 es `fuera_de_cobertura`.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `mindefensa_homicidios_municipio` | alto | nueva: por modalidad, con mujeres, feminicidios y arma de fuego |

## Decisiones

- **2026-11-02, error 12 de la revisión de valor:** faltaba la pregunta de seguridad más común
  («¿cuántos homicidios lleva Cali este año?»). Medicina Legal solo llega a 2024, y de la Policía el
  catálogo solo tiene los homicidios en accidentes de tránsito.
  - Tiene la misma forma que las de Policía: municipio y año, y el `complemento` dice hasta qué mes
    publica la fuente en todo el país, con aviso si el año está incompleto.
  - Se agrupa por modalidad presunta, de la que tiene más víctimas a la que menos.
  - El tope del canario es de 20 s: se midió de 5 a 12 s.
- **Pendiente:** «MASACRES» (`u8eq-92tb`), del mismo ministerio, para contrastar con el CNMH.
