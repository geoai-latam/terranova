# Sistema de diseño de Terrnova (v4)

La fuente de verdad es el sitio en producción: los tokens viven en `web/publico/estilo.css` (`:root`)
y las páginas las genera `web/construir.py` desde el catálogo. Este documento dice las reglas que no
se leen en el CSS. Si algo de aquí contradice el CSS, se corrige el que esté mal y se dice en el PR.

El sistema nació como artifact de claude.ai (v3, 29-10-2026). Esa versión quedó atrás en radios,
sombras, cifras y en el discurso de «agentes que hacen el trabajo»; manda este documento.

## Cómo se ve

Sobria y técnica, con el oficio de un buen mapa. El carácter lo ponen los datos reales: predios en
3D, respuestas con su huella y cifras con su fecha. No hay ilustraciones decorativas, brillos,
degradados decorativos ni fotos de stock; las figuras isométricas explican, no adornan.

- Fondo blanco roto con sesgo verde (`--fondo`), tinta verde muy oscura y **un solo acento ámbar
  por vista**: el botón principal o lo que hay que mirar.
- Una familia, Geist, para todo el texto. Geist Mono solo para datos: campos rt/1, rutas de API,
  huellas, cifras en tablas y pies de fuente.
- **Radios pequeños** en todo (2 a 6 px): se lee editorial y técnico, no como un kit de tarjetas.
  Los botones también (`--radio-pill` vale 3 px; el nombre es histórico).
- **Filetes, no tarjetas:** los bloques se separan con un filete superior de 1 px (`.bloque`); el que
  importa lleva 3 px en ámbar (`.bloque.vivo`). Sin sombra de tarjeta (`--sombra-tarjeta: none`);
  solo flota lo que de verdad flota (`--sombra-flotante`).
- El símbolo de la puerta vive en el logo y en la portada. No se repite como decoración.

## Lo que no se hace («AI slop»)

El dueño rechazó explícitamente:

- serif itálica de acento, o una sola palabra del titular en otro color o peso;
- cejillas en mono MAYÚSCULA espaciada encima de cada título, y chips tipo «● en producción»;
- brillos, arcos y degradados decorativos, rejillas de tarjetas redondeadas con sombra gris;
- numerar (01 / 02 / 03) lo que no es una secuencia;
- conmutadores que nadie usa (el «Geo / No geo» del héroe salió: las dos respuestas se muestran a
  la vez).

Las cejillas de las portadas interiores y las etiquetas en mayúsculas (`.bloque .num`) ya salieron.

## Color

Tokens en `estilo.css`. Solo hay tema claro en la web.

| Rol | Tokens | Uso |
|---|---|---|
| Fondo | `fondo`, `superficie`, `superficie-2` | Blanco roto y dos grises verdosos |
| Bloque oscuro | `superficie-invertida`, `bosque-900/800/700` | Bandas oscuras (servicios), consola, pantallas de las figuras |
| Texto | `tinta`, `tinta-suave`, `tinta-tenue` | Todos ≥ 4,5:1 sobre fondo y superficie |
| Acento | `acento` (texto, `ambar-700`), `acento-relleno` (`ambar-500`) | Uno por vista. Ámbar sobre claro solo como relleno con tinta encima |
| Verificado | `verificado` (`teal-700`; `teal-400` sobre oscuro) | Huella, procedencia, enlaces |
| Estados rt/1 | `estado-encontrado`, `estado-no-encontrado`, `estado-parcial`, `estado-fuera-de-cobertura`, `error` | `no_encontrado` es neutro, no rojo: es una respuesta válida |
| Líneas | `linea`, `linea-fuerte` | Filetes; bordes de campos y botón secundario (≥ 3:1) |

El verde bosque es la marca. El ocre (`ocre-400`) es solo para mapas y gráficos. En gráficos, las
series van tinta, teal, ámbar, ocre; la rejilla en `linea` y la serie que importa en ámbar.

## Tipografía

Geist 700 para titulares con interletrado negativo (`.t1` −0,04 em, `.t2` −0,032 em), 400 para el
texto, 600 para la interfaz. Titulares con `text-wrap: balance`, párrafos con `pretty`, cifras con
`tabular-nums`. Rótulos en minúscula normal (`.rotulo`, 14 px, `tinta-tenue`). Texto corrido de
hasta ~68 caracteres por línea (`.entrada` max 640 px).

## Retícula

Contenido hasta 1.200 px (`--ancho`), margen lateral `clamp(16px, 4.5vw, 56px)`, secciones separadas
`clamp(64px, 9vw, 112px)`. Ritmo interno en múltiplos de 8. Rejillas `.r2/.r3/.r4` que bajan a una
columna en 640 px. Toda página se revisa a 1440 y 390 px sin desborde horizontal.

## Cómo se escribe

Español, frases cortas, voz activa. Las cosas con el nombre que les da quien las usa: predio,
fuente, licencia, expediente.

- **Solo lo que es verdad.** Toda cifra sale del catálogo o de los datos (`construir.py`), nunca a
  mano, y lleva su fuente y su fecha. Antes de publicar texto nuevo se contrasta con el código.
- Los conteos solo cuentan fuentes **publicadas** (un borrador no se anuncia). No se nombran
  herramientas con el canario en rojo ni fuentes sin uso comercial (los usuarios aduaneros de la DIAN,
  sin fines de lucro). El normograma de la DIAN sí se nombra: texto oficial libre (Ley 23 de 1982, art. 41).
- **No se dice que un agente hace el trabajo:** lo hace el equipo, con herramientas.
- «No encontrado» es una respuesta; «no se pudo» es un error con su código.
- Lo que existe, en presente; lo que viene, marcado como visión.
- Nada de «potenciado por IA», «revolucionario» ni «mágico».
- Ningún ejemplo busca personas por nombre o cédula (ADR-0014). Los ejemplos son lugares y predios.
- Lo inventado lleva el sello `ilustrativo` (`.sello-i`). Lo real lleva fecha y fuente.
- No se muestran clientes, logos ni testimonios que no existen. No se nombra ArcGIS: «el sistema
  del cliente» o «su SIG».
- Números en formato colombiano (0,56 s; 1.510; 6,1 M); fechas DD-MM-AAAA en texto e ISO en la API.

| Así sí | Así no |
|---|---|
| Consulta un punto y recibe el predio, su fuente y su huella. | Desbloquea el poder de los datos geoespaciales con IA. |
| La fuente no respondió (IGAC, 12 s). Reintenta en 5 min. | Error. Inténtalo más tarde. |

## 3D (three.js)

El 3D solo va con datos reales y cuando ayuda a leerlos.

- **Escena:** solo el héroe, `escena-predios.js` (predios SINIC de Santa Marta con calles, barrio y
  el predio consultado; `comun3d.js` tiene lo común). Lo demás son figuras isométricas en SVG (abajo).
- **Cámara ortográfica** siempre, para que las medidas no se deformen. Se gira arrastrando, sin zoom
  con la rueda (secuestraría el scroll). Sin interacción, gira despacio.
- `prefers-reduced-motion`: la escena queda quieta. Sin WebGL: queda la imagen equivalente.
- Colores desde los tokens; sombreado plano, sin luces que cambien los colores de marca.
- Lo que no es dato se dice: el grosor de los predios y la subida del consultado son simbólicos.

## Figuras isométricas (Anatomy)

Todas las ilustraciones del sitio, menos el héroe 3D, son figuras isométricas en SVG que explican una
idea con un objeto que se reconoce: un bastidor (capas), un banco con barrera (la ruta de una
pregunta), un fichero (la prueba de una respuesta), una banda de inspección (debida diligencia), una
mesa de relojes con trazador (tableros), un puesto de guardia con buzones (vigilancia), un tablero de
conmutación (asistentes) y una maqueta de Colombia (cobertura SINIC). Siguen el método de
[Anatomy](https://github.com/wheresryan22/anatomy) (MIT), cuyo kit está en `web/figuras/kit`.

- **Integradas, nunca tarjetas:** sin borde, sin fondo propio y sin cabecera «Fig. n · título». La
  figura vive sobre el fondo de su sección (`--papel`), alineada a la retícula, con el texto al lado
  (`.con-fig`) o encima. Debajo, una línea mono: la lectura en vivo arriba y la pista (y el sello
  `ilustrativo`, neutro) abajo, alineadas al borde izquierdo del dibujo.
- **El objeto es la explicación:** piezas reales con volumen (patas, rieles, tornillos, placas,
  clavijas), no cajas con flechas. Cada línea termina en algo; se comprueba con el `lines.mjs` de
  Anatomy (0 extremos sueltos).
- **Coherencia:** la misma cámara (elevación 30°; acimut 57–58°, 45° en la ruta y 72° en la maqueta
  para que el país se reconozca), la misma escala de construcción (`comun.mjs`, `encuadre`), el mismo
  grosor de línea (0,6 px) y las mismas piezas de banco (`base`, `regla`). Cada figura llena su
  columna.
- **Verdad:** todo lo que muestran sale de `construir.py` (catálogo y `datos/co.json`) vía
  `web/figuras/datos.json`; lo inventado lleva el sello `ilustrativo` y la etiqueta accesible lo dice.
- **Color (las figuras sí lo llevan; la página sigue con un solo acento):** cada pieza tiene un
  material de la paleta (`m-bosque`, `m-verde`, `m-teal`, `m-agua`, `m-ocre`, `m-ambar`, `m-metal`,
  `m-acero`, `m-pantalla`, `m-trabajo`, `m-papel`; ver `estilo.css`). La cara de arriba aclara un 16 %,
  los costados se oscurecen hacia `bosque-900` (sombra con tono, nunca gris) y el filo es el mismo
  color más hondo; el halo es verde translúcido. Encendida, la pieza aclara y su filo pasa a ámbar.
  Cada figura tiene 3–4 colores y uno protagonista distinto: bastidor y fichero teal, ruta teal,
  revisión ocre, tablero agua, vigilancia azul (`estado-fuera-de-cobertura`), asistente ámbar y
  cobertura de teal a ámbar según el conteo. Los estados usan su color del sistema solo donde hay un
  estado (la bandera «revisar» en `estado-parcial`). Sin degradados, brillos ni neón.
- **Vida:** además del ciclo principal (6–10 s), un movimiento ambiente calmado mientras la figura
  está en vista: pilotos que titilan a ritmos distintos, pantallas que escriben, paquetes de datos que
  recorren cables y vigas, una cinta que avanza, agujas que tiemblan, un cordón que se mece, un sello
  que cae con rebote. Las piezas entran con un leve resorte. Fuera de la vista se pausa; con
  `prefers-reduced-motion` quedan quietas, completas y a color.
- **Texto:** como mucho un rótulo grabado por figura («Datos», «Terrnova», «rt/1»); lo demás va en la
  lectura y en el texto de la sección, en minúscula.
- **Movimiento:** calmado, con tiempo; recorre solo cuando nadie toca, el puntero y las flechas
  eligen, y fuera de la vista no corre. Con `prefers-reduced-motion` queda quieto y completo.
- **Peso:** los SVG van aparte (`web/publico/img/figuras/`) y `figuras.js` los trae al acercarse a la
  vista; el hueco tiene su proporción para que la página no salte.
- **Construir:** `uv run python web/construir.py` escribe los datos y, si hay Node, dibuja
  (`node web/figuras/construir.mjs`); la huella de datos + scripts + kit va en cada SVG y `--revisar`
  falla si alguno quedó viejo (el CI no tiene Node).

## Logo y aliados

Tres curvas de nivel forman un arco (puerta y colina en planta); el punto ámbar es el lugar
consultado. «Terrnova» en Geist 700, interletrado −4 %. No se gira ni cambia el color del punto.

GeoAI LATAM y Atalaya Mapas son proyectos hermanos, nunca clientes, siempre con su logo oficial. El
de Atalaya Mapas está pendiente: hasta tenerlo se escribe su nombre.

## Ver el sitio en local

```bash
uv run python web/construir.py                 # regenera web/publico desde el catálogo
uv run python web/servir.py                    # http://localhost:8080, como lo sirve Caddy
uv run --with playwright python web/capturar.py 1440 / "#servicios"   # captura de una sección
uv run pytest tests/test_web.py -q             # las páginas no quedaron viejas
```

`capturar.py` usa Edge con GPU (las escenas WebGL no pintan sin ella) y deja las capturas en
`capturas/`, que no se versiona.
