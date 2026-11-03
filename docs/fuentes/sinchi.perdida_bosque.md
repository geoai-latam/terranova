# SINCHI, cambio del bosque en la Amazonia 2022-2024 (`sinchi.perdida_bosque`)

La capa multitemporal de pérdida de bosque de la Amazonia colombiana del Instituto SINCHI (SIAT-AC):
`MAC_DatosAbiertos/TMAPB_Region_100K_2022_2024`, capa 0, escala 1:100.000. Licencia CC BY 4.0
(verificada el 2026-10-28 en el catálogo de datos del SIAT-AC).

## Qué publica

Cuatro multipolígonos que cubren la Amazonia colombiana, uno por clase del cambio del bosque entre
2022 y 2024:

- `Perdida`: deforestado en el periodo (286 625 ha);
- `Conservado`;
- `Recuperado`;
- `Otras coberturas`: no era bosque.

## Cómo se sirve

- Desde una copia de Terrnova del 2026-10-28, simplificada a ~56 m (`tolerancia` 0,0005°).
- Por la geometría, cada clase se copia como una página propia (`por_pagina: 1`).
- Fuera del rectángulo amazónico (-77,9; -4,3; -66,8; 4,2) la respuesta es «fuera de cobertura».

## Trampas medidas

1. **No es una prueba EUDR.** El reglamento europeo de deforestación pide demostrar que no hubo
   deforestación después del 31 de diciembre de 2020. Esta capa mide de 2022 a 2024 y no ve 2021:
   «Conservado» aquí no prueba lo que la EUDR exige.
2. **Escala gruesa.** A 1:100.000 y con ~56 m de simplificación, no sirve para el borde de una
   finca.
3. **Una sola clase por punto.** Leticia urbana sale «Otras coberturas»; un punto cerca de La
   Macarena sale «Perdida» (el canario).

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `sinchi_perdida_bosque_en_punto` | medio | v2: dice el `periodo` y que es un indicio, no una prueba EUDR |

## Decisiones

- **2026-11-03, revisión de valor (v2):**
  - La descripción ya no dice «sirve para la debida diligencia EUDR». Dice que es un indicio de
    deforestación reciente y por qué no alcanza.
  - La respuesta trae `periodo: 2022-2024`.
- **Pendiente:** una capa con corte en 2020, como el bosque/no bosque anual del IDEAM (SMByC), para
  lo que la EUDR sí pide.
