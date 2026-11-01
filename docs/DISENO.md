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
  huellas, cifras en tablas, lecturas de figuras y pies de fuente. Pistas, migas, rótulos y sellos
  van en Geist; nada en mayúscula espaciada.
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

Tokens en `estilo.css` (`:root`). Solo hay tema claro en la web.

### La página

| Rol | Tokens | Uso |
|---|---|---|
| Fondo | `fondo`, `superficie`, `superficie-2` | Blanco roto y dos grises verdosos |
| Bloque oscuro | `superficie-invertida`, `bosque-900/800/700` | Bandas oscuras, la consola del héroe, pantallas de las figuras |
| Texto | `tinta`, `tinta-suave`, `tinta-tenue` | Todos ≥ 4,5:1 sobre fondo y superficie |
| Acento | `acento` (texto, `ambar-700`), `acento-relleno` (`ambar-500`) | **Uno por pantalla: el botón principal.** El botón del menú es secundario; las pestañas elegidas se marcan en tinta, no en ámbar |
| Verificado | `verificado` (`teal-700`; `teal-400` sobre oscuro) | Enlaces y, en el sobre, lo que prueba la respuesta |
| Estados rt/1 | `estado-encontrado`, `estado-no-encontrado`, `estado-parcial`, `estado-fuera-de-cobertura`, `error` | `no_encontrado` es neutro, no rojo: es una respuesta válida |
| Líneas | `linea`, `linea-fuerte` | Filetes; bordes de campos y botón secundario (≥ 3:1) |

El verde bosque es la marca. En gráficos, las series van tinta, teal, ámbar, ocre; la rejilla en
`linea` y la serie que importa en ámbar.

### Las figuras: color por papeles

Cada color tiene un papel, no un adorno. Las rampas están en OKLab, derivadas de los tokens de la
marca, y van del techo (`-0`) a la cara más oscura (`-4`); una cara toma su tono por orientación,
con la luz fija a la cámara (la regla del kit de Anatomy).

| Papel | Tokens | Cuánto | Uso |
|---|---|---|---|
| Estructura | `estructura-0…6` (#F4F8F1 → #B9BDB6) | 70–80 % del área | Bancos, bases, armazones, predios vecinos. Las bases van dos escalones más hondo (`2…6`) |
| Líneas | `linea-tenue`, `linea-baja`, `linea-media`, `linea-alta`, a 0,6 px | — | Ranuras y costuras (tenue), marcas menores (baja), filos (media), lo que se lee (alta) |
| Sujeto | `sujeto-teal-*`, `sujeto-agua-*`, `sujeto-ocre-*`, cada uno con su `-filo` | 15–25 % | **Un** material de color por figura, distinto entre figuras para que la página tenga color |
| Material oscuro | `oscuro-0…4` con `oscuro-filo` claro | — | Pantallas y chasis; el filo es claro para que lo oscuro no se funda |
| Acento | `acento-0…4` con `acento-filo` (#8F570B) | ≤ 3–5 % | Ámbar en **una** pieza: la que está pasando. Ninguna cara ámbar mayor de ~40 × 40 px |
| Estado | `estado-vivo`, `estado-copia`, `estado-no-se-pudo`, `estado-vacio` | marca de 3–6 px | Vivo = punto teal; copia = anillo ocre; no se pudo = aspa en tinta; no encontrado = anillo vacío. Nunca superficie |
| Sombra | `halo` | — | Sombra de contacto horneada (escalones translúcidos), sin desenfoque |

Reglas: neutros + un material + un acento por figura; el ocre nunca junto al ámbar; el azul de
estado («fuera de cobertura») no es material. En `estilo.css` cada pieza lleva `m-<material>` y el
material es una rampa (`--c0…--c4`, `--filo`, `--pliegue`); encendida (`data-lit`), sube un
escalón y su filo pasa a ámbar.

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
- Lo inventado lleva el sello `ilustrativo` (`.sello-i`, un solo estilo: Geist 12 px, neutro, con
  filete). Lo real lleva fecha y fuente.
- No se muestran clientes, logos ni testimonios que no existen. No se nombra ArcGIS: «el sistema
  del cliente» o «su SIG».
- Números en formato colombiano (0,56 s; 1.510; 6,1 M); fechas DD-MM-AAAA en texto e ISO en la API.

| Así sí | Así no |
|---|---|
| Consulta un punto y recibe el predio, su fuente y su huella. | Desbloquea el poder de los datos geoespaciales con IA. |
| La fuente no respondió (IGAC, 12 s). Reintenta en 5 min. | Error. Inténtalo más tarde. |

## El héroe: la escena de predios (three.js)

El 3D solo va con datos reales y cuando ayuda a leerlos. El héroe es la animación principal del
sitio y no se rediseña con las figuras: el dueño la quiere como está.

- **La escena:** los predios reales del SINIC (`datos/sm.json`) alrededor del punto consultado en
  Santa Marta, a todo lo ancho detrás del texto, con las calles de OpenStreetMap
  (`datos/calles.json`) rotuladas, escala y norte. Al entrar, la cámara baja y los predios crecen
  desde el punto; luego gira despacio. El predio consultado sube cuando la consola muestra su
  respuesta en la consola y sale una onda del punto. `js/escena-predios.js` y `js/comun3d.js`; mientras carga,
  la imagen de respaldo (`img/predio-santamarta.webp`).
- **Dos arreglos que no cambian cómo se ve:** con movimiento reducido dibuja un solo cuadro (y otro
  solo si el lector arrastra o cambia el tamaño), y el giro y la subida van por tiempo (dt), no
  por cuadros.
- **Accesibilidad:** la imagen accesible es el lienzo (`role="img"`); la lectura con el enlace de
  OpenStreetMap queda fuera y se puede tocar.
- **La consola rt/1** va encima de la escena, a la derecha: tres respuestas reales de producción
  (predio, empresa y norma) en pestañas, que se reproducen por turnos con su fecha de captura
  (DD-MM-AAAA). Una guía une la respuesta con el predio consultado, que sube cuando llega.
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
  (`.con-fig`) o encima. Debajo, la lectura en vivo en mono (es dato) y la pista en Geist 13 px,
  que aparece al pasar o enfocar, con el sello `ilustrativo` si toca.
- **El objeto es la explicación:** piezas reales con volumen (patas, rieles, tornillos, placas,
  clavijas), no cajas con flechas. Cada línea termina en algo; se comprueba con el `lines.mjs` de
  Anatomy (0 extremos sueltos).
- **Coherencia:** la misma cámara (elevación 30°; acimut 57–58°, 45° en la ruta, 72°
  en la maqueta de cobertura para que el país se reconozca), la misma escala de construcción (`comun.mjs`, `encuadre`), el mismo
  grosor de línea (0,6 px) y las mismas piezas de banco (`base`, `regla`). Cada figura llena su
  columna.
- **Verdad:** todo lo que muestran sale de `construir.py` (catálogo y `datos/co.json`) vía
  `web/figuras/datos.json`; lo inventado lleva el sello `ilustrativo` y la etiqueta accesible lo dice.
  Ninguna nombra el DANE ni una herramienta que no se vende (`datos.json` lleva `usadas` y
  `tests/test_web.py` lo comprueba), y cada «como» de la revisión casa con la entrada real de sus
  herramientas (lo comprueba el build).
- **Color:** por papeles (ver «Color»): neutros de estructura, un material de color propio por
  figura y un solo acento ámbar en la pieza que está pasando. Sin degradados, brillos ni neón.

  | Figura | Material | El ámbar |
  |---|---|---|
  | capas | teal (Datos, `teal-fuerte`) | el dato que sube por el cable |
  | ruta | agua (columnas de entidades) | la ficha de la pregunta y la tapa de la columna que responde |
  | prueba | bosque (el fichero, filo claro) | la pestaña de la ficha que se lee |
  | revisión | ocre (fichas, pila, motor, bandeja) | la banderita de la estación que encuentra algo |
  | tablero | agua (relojes, `agua-fuerte`) | la aguja del reloj elegido |
  | vigilancia | teal (buzones, `teal-fuerte`) | la banderita levantada |
  | asistente | bosque (el panel, filo claro) | el piloto de la boca conectada |
  | cobertura | una rampa agua → teal hondo (`m-cob0…4`) | la columna encendida |

  Lo que aparece o se va de color lo hace con la escala, no con la opacidad (un ámbar a medio
  fundir sobre gris se ve oliva); las luces cambian de golpe, como una luz.
- **Movimiento con significado:** cada figura cuenta un ciclo: reposo → disparo → tránsito
  (400–700 ms) → resultado → reposo de 2,6 s con todo quieto. Solo se mueve lo que actúa; la
  estructura nunca. Ambiente solo si es un estado real: el lector de la vigilancia late cada 3 s
  mientras la figura está viva y quieta. Corre al entrar en vista (dos ciclos como mucho), vuelve con
  el puntero (elige por posición), el toque, el foco o las flechas y se puede interrumpir (mezcla de
  280 ms desde lo que se veía). Curvas: entrada `cubic-bezier(0, 0, .3, 1)`, salida
  `cubic-bezier(.4, .14, 1, 1)`, resorte críticamente amortiguado; subamortiguado solo en las agujas
  del tablero (oscilan al asentarse). La lectura cambia en el instante en que llega el dato. Con
  `prefers-reduced-motion`, un cuadro del estado resultado.
- **Cómo está hecho (`js/figuras.js`):** cada figura es una función pura del tiempo,
  `pose(turno, t)`, que pone las piezas vivas (canales x, y, opacidad, escala y uno propio: un
  ángulo, un avance) y devuelve la lectura de ese instante. Un planificador único deja viva solo la
  figura más visible y la mueve con `requestAnimationFrame`; `window.__figuras.ver(nombre, turno, ms)`
  pide cualquier instante (hojas de contacto y pruebas). Lo que gira en un plano (el brazo de la
  barrera, la banderita, las agujas) se dibuja en coordenadas del plano con su matriz y gira con
  `rotate`; lo que crece (barras, columnas) escala en un eje desde su base (`data-eje`).
- **Rendimiento:** dos capas por figura: la fija y la viva (las piezas que se mueven y lo que las
  tapa), en su propio `<svg>` encima, movida solo con `transform` y `opacity`; trayectorias y series
  precalculadas en el build (nada de `getPointAtLength` ni de animar `d`); sin `filter: blur` (sombras
  horneadas en escalones); a lo sumo 60 cuadros por segundo y 30 con puntero grueso o
  `hardwareConcurrency ≤ 4`; cero cuadros en reposo. Sin `will-change`: promover la capa viva al
  empezar cada ciclo costaba ~50 ms a CPU 4× (medido) y no ahorraba. Presupuesto medido a 390 px con
  CPU 4×: ninguna tarea del hilo principal por encima de 33 ms en ninguna figura.
- **Texto:** pocos rótulos grabados («Datos», «Terrnova», «rt/1»; las siglas de las entidades en el
  tablero del asistente, que es lo que la clavija elige); lo demás va en la lectura (una línea) y en la
  pista (el detalle: licencia, entidad), en minúscula.
- **Peso:** los SVG van aparte (`web/publico/img/figuras/`) y `figuras.js` los trae al acercarse a la
  vista; el hueco tiene su proporción para que la página no salte.
- **Construir:** `uv run python web/construir.py` escribe los datos y, si hay Node, dibuja
  (`node web/figuras/construir.mjs`); la huella de datos + scripts + kit va en cada SVG y `--revisar`
  falla si alguno quedó viejo (el CI no tiene Node).

## Logo y aliados

Tres curvas de nivel forman un arco (puerta y colina en planta); el punto ámbar es el lugar
consultado. «Terrnova» en Geist 650 a 20 px con interletrado +2 %: con −4 % la «rn» se pegaba y a
1x se leía «Termova». Se comprueba con una captura a 1x. En el pie, sobre bosque, la puerta va clara
(#F3EFE4) y el punto sigue ámbar. No se gira ni cambia el color del punto.

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
