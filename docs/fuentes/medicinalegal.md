# Medicina Legal, lesiones fatales de causa externa (`medicinalegal.*`)

Tres conjuntos de datos.gov.co del Instituto Nacional de Medicina Legal y Ciencias Forenses, con la
misma forma. Licencia CC BY-SA 4.0. Se consultan en vivo. Comparten este archivo.

| Fuente | Conjunto | Herramienta |
|---|---|---|
| `medicinalegal.homicidios` | `vtub-3de2` | `medicinalegal_homicidios_municipio` |
| `medicinalegal.suicidios` | `f75u-mirk` | `medicinalegal_suicidios_municipio` |
| `medicinalegal.muertes_accidentales` | `irg9-q5fx` | `medicinalegal_muertes_accidentales_municipio` |

## Qué publica

Una fila por víctima, según las necropsias. Son cifras forenses, distintas de las denuncias de la
Policía. Cada fila trae datos sensibles de la persona (estado civil, escolaridad, etnia…): Terrnova
solo sirve conteos por municipio, año, sexo y mecanismo causal.

Víctimas por año en todo el país (medido el 2026-11-05):

| Año | Homicidios | Suicidios | Muertes accidentales |
|---|---|---|---|
| 2015 | 11 585 | 2 068 | 2 675 |
| 2020 | 11 326 | 2 420 | 2 812 |
| 2024 | 14 021 | 3 014 | 4 181 |
| 2015 a 2024 | 125 284 | 26 558 | 33 254 |

Las muertes accidentales no incluyen las de tránsito.

## Campos que importan

- `codigo_dane_municipio`: el municipio del hecho, en texto y sin el cero inicial (5001 es
  Medellín). Se compara como número.
- `a_o_del_hecho`: el año, en texto.
- 999 es «Sin información» de municipio.

## Cobertura

- De 2015 a 2024. Un año fuera de ahí sale «fuera de cobertura» con el rango (Medellín 2025 y 2014,
  2026-11-05).
- Casi todas las víctimas tienen municipio. Sin municipio (código 999) en 2024: 3 homicidios,
  1 suicidio y 2 muertes accidentales. El año con más: 2016, con 67 homicidios.

## Trampas medidas

1. **Un vacío salía sin explicación.** Providencia (88564) no tiene homicidios en 2024 ni muertes
   accidentales en 2023: la respuesta era «no encontrado» sin decir que la fuente sí se consultó y
   no tiene víctimas ahí (2026-11-05).
2. **Algunas consultas tardan.** Chía 2024, suicidios: 10,6 s en producción en la primera llamada
   (2026-11-05); las demás, 1,1-1,3 s.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `medicinalegal_homicidios_municipio` | alto | Medellín 2024: 327 víctimas (301 hombres, 26 mujeres); 147 por arma de fuego en hombres |
| `medicinalegal_suicidios_municipio` | alto | Cali 2015: 70 víctimas |
| `medicinalegal_muertes_accidentales_municipio` | medio | Chía 2024: 15 víctimas; no incluye tránsito |

## Decisiones

- **2026-11-05, revisión de valor:** las tres dicen por qué un vacío: Medicina Legal no registra
  víctimas en ese municipio y año, y cuenta por el municipio donde ocurrió el hecho.
- **Sin medir:** si el año de la fuente se actualiza con cifras de 2025.
