# Función Pública: SUIT, trámites inscritos (`funcionpublica.suit_historico`, `funcionpublica.suit_oferta`)

El Sistema Único de Información de Trámites (SUIT) de Función Pública, en datos.gov.co, con licencia
CC BY-SA 4.0. Se consulta en vivo.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `funcionpublica.suit_historico` | `dd24-8p6w` | `suit_tramites_entidad` |
| `funcionpublica.suit_oferta` | (ver su ficha) | `suit_oferta_tramites_entidad` |

## Qué publica

- **Histórico:** por entidad y mes, los trámites inscritos en el SUIT, presenciales, en línea y en
  total.
- **Oferta:** las solicitudes de cada trámite, hasta 2023.

## Campos que importan

- `nit`. **Un NIT puede tener varias entidades:** el de Bogotá (899999061) agrupa 18 secretarías,
  cada una en su fila.
- `a_o` y `mes` son texto. En orden de texto «9» va después de «12», así que se ordena con
  `mes::number`.
- Las cifras (`tr_mites_inscritos_*`) son texto, y a veces el texto es «NULL».

## Cobertura

Medido el 2026-11-02:

- de noviembre de 2018 a diciembre de 2020;
- enero de 2021 tiene 43 filas, todas con «NULL» en las cifras;
- la ficha de datos.gov.co no cambia desde el 2025-05-28.

## Trampas medidas

1. **Lo más viejo primero.** Las primeras cifras eran de noviembre de 2018 (Ministerio de
   Educación: 18).
2. **La serie se detuvo en 2020** y nada lo decía.
3. **«Lo último» de un NIT no es una fila.** En el NIT de Bogotá, la primera fila es una sola
   secretaría (Ambiente, 32). El NIT suma 306 trámites en diciembre de 2020.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `suit_tramites_entidad` | bajo → medio | v2: lo más reciente primero; la última cifra del NIT, sumando sus entidades; aviso de que la serie paró en 2020 |
| `suit_oferta_tramites_entidad` | medio | pendiente: el mismo trámite sale tres veces (patrón F) |

## Decisiones

- **2026-11-02, patrón E de la revisión de valor:**
  - Las filas «NULL» se filtran, y el orden es `a_o DESC, mes::number DESC`.
  - La última cifra del NIT sale de un complemento, agrupado por mes: `ultimo_anio`,
    `ultimo_mes`, `tramites_total_ultimo`, `tramites_en_linea_ultimo` y `entidades_del_nit`.
  - Un aviso dice que la serie se detuvo en diciembre de 2020 y remite a
    `suit_oferta_tramites_entidad`.
