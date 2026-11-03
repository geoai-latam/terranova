# ESA WorldCover 2021 (`esa.worldcover`)

El mapa mundial de cobertura del suelo de la Agencia Espacial Europea, versión 200, del año 2021,
a 10 m. Son COG de 3°×3° en S3 (`esa-worldcover/v200/2021/map`). Licencia CC BY 4.0. Global.

## Qué publica

Cada píxel de 10 m es una clase (los nombres son los que usa `imagery-mcp`):

| Código | Clase |
|---|---|
| 10 | Árboles |
| 20 | Arbustal |
| 30 | Pastizal |
| 40 | Cultivos |
| 50 | Construido |
| 60 | Suelo desnudo / escasa vegetación |
| 70 | Nieve y hielo |
| 80 | Agua permanente |
| 90 | Humedal herbáceo |
| 95 | Manglar |
| 100 | Musgo y liquen |

El mapa está cerrado: no se actualiza.

## Cómo se sirve

`imagery-mcp` lee del COG la ventana de ±0,005° alrededor del punto (un cuadro de ~1,1 km). Cuenta
los píxeles por clase y da el área en km² y el porcentaje. La clase dominante es la de más área.

## Trampas medidas

1. **Es 2021.** No muestra cambios posteriores, y antes la respuesta no lo decía: solo la ficha.
2. **Es un cuadro, no el punto.** En Kennedy (Bogotá), el cuadro es 90,8 % construido, 5,2 %
   pastizal y 2,7 % árboles (el canario, medido el 2026-10-22).

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `esa_cobertura_suelo_en_punto` | alto | v2: cada clase trae `anio: 2021` |

Probada en producción el 2026-11-03: Kennedy (canario); centro de Medellín (-75,57; 6,25),
96,97 % construido.

## Decisiones

- **2026-11-03, revisión de valor (v2):** el año va en la respuesta, en cada clase (derivado
  `fijo`), y no solo en la ficha.
