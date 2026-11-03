# INS: calidad del agua, IRCA (`ins.calidad_agua_irca`)

Un conjunto de datos.gov.co, publicado por el Instituto Nacional de Salud con licencia CC BY-SA 4.0.
Se consulta en vivo.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `ins.calidad_agua_irca` | `nxt2-39c3` | `ins_calidad_agua_municipio` |

## Qué publica

El índice de riesgo de la calidad del agua para consumo humano (IRCA) de cada municipio y año, de la
vigilancia del INS (SIVICAP): el total, el urbano y el rural, cada uno con su nivel de riesgo (sin
riesgo, bajo, medio, alto, inviable sanitariamente). 0 a 100: menos es mejor.

## Campos que importan

- `municipiocodigo`: el DIVIPOLA, como texto de 5 dígitos.
- `irca`: número.
- `ircaurbano` e `ircarural`: **texto**, con «ND» cuando no hubo dato. Lo demás son números.
  Terrnova los da como número y deja vacío el «ND»; igual con sus niveles de riesgo.

## Cobertura

Medido el 2026-11-02: 19 160 filas, de 2007 a 2024. 2024 trae 1 038 municipios.

## Trampas medidas

1. **Lo más viejo primero.** La v1 ordenaba por año ascendente: la pregunta «¿es potable hoy?»
   quedaba al final de 18 filas.
2. **Municipios que dejaron de reportar.** Bojayá tiene dos años (2017: 96,3, «Inviable
   sanitariamente»; 2019: 69,5, «Riesgo alto») y nada después. El Peñón (Bolívar) llega a 2019.
   Que no haya dato reciente no dice que el agua mejoró.
3. **«ND» es frecuente en lo rural:** 9 615 filas, frente a 1 268 en lo urbano.
4. **El total puede existir sin urbano ni rural** (Bojayá 2017).

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `ins_calidad_agua_municipio` | alto | v2: lo más reciente primero, resumen del último año, «ND» vacío, aviso si el dato es viejo |

## Decisiones

- **2026-11-02, patrón E de la revisión de valor:**
  - Orden por año descendente. Arriba van `ultimo_anio`, `irca_ultimo_anio` y
    `nivel_riesgo_ultimo_anio`.
  - Si el último año del municipio es anterior al de la fuente (2024), un aviso lo dice. El año
    tope está escrito en el aviso: hay que moverlo cuando el INS publique 2025.
  - «ND» sale vacío (`vacios`), y urbano y rural pasan a número.
