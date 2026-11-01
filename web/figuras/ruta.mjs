// Fig. ruta: un banco con la terminal del agente, un lector de llave, una barrera con el nombre de
// Terrnova y un tablero con una columna por entidad (alta según sus fuentes, todas iguales de
// color). La pregunta es una ficha ámbar que corre por la regla: el lector valida la llave, la
// barrera se levanta, la ficha llega a la columna de su entidad (cuya tapa se enciende) y la
// respuesta vuelve a la terminal. Un solo ciclo de unos 3 s por pregunta.
import { D, L, S, encuadre, k, lampara, matrizPlano, r1, sombra, svgDe } from "./comun.mjs";

const tramo = (a, b, P) => k.segment(a, b, P);

export function ruta(DATOS, huella) {
  const { turnos, otras } = DATOS.ruta;
  const BANCO = { x: -14, y: -144, w: 296, d: 166, r: 4 };
  const TAB = { x: 104, y: -130, w: 168, d: 124, r: 2 };
  const PASO = 19.5, LADO = 13, X0 = 111, Y0 = -20; // columna (fila 0, col 0): x X0..X0+LADO, y Y0..Y0+LADO
  const COLS = 8, FILAS = 6;
  const ZT = 4; // cara del tablero
  const alto = (n) => 6 + 1.9 * n;
  const EJE = [89, -13.5, 26.2]; // eje de la barrera (gira en el plano x = 89)
  const LARGO = 30.1;
  const { P, ancho, alto: altoV } = encuadre(
    [...k.boxCorners(BANCO, -16, 0), [X0, Y0 - 5 * PASO, ZT + alto(34)], [EJE[0], EJE[1], EJE[2] + LARGO + 4], [0, -24, 42]],
    { azimuth: 45 },
  );
  const at = (p) => k.iso(p, P);
  const fija = [];
  const viva = [];

  // celdas: las entidades de los turnos en la fila de adelante (cols 1, 4, 6); el resto de atrás
  // hacia adelante, de más a menos fuentes; las dos que sobran, en las esquinas de adelante
  const celdas = new Map();
  const colTurno = [1, 4, 6];
  turnos.forEach((t, i) => celdas.set(`0,${colTurno[i]}`, { n: t.fuentes, turno: i }));
  const libres = [];
  for (let f = FILAS - 1; f >= 0; f--) for (let c = 0; c < COLS; c++) if (!celdas.has(`${f},${c}`)) libres.push([f, c]);
  const sobran = libres.length - otras.length;
  if (sobran < 0) throw new Error("no caben las entidades en el tablero");
  const vacias = new Set(["0,0", `0,${COLS - 1}`].slice(0, sobran));
  const usar = libres.filter(([f, c]) => !vacias.has(`${f},${c}`));
  usar.forEach(([f, c], i) => celdas.set(`${f},${c}`, { n: otras[i] }));
  const pie = (f, c) => [X0 + c * PASO, Y0 - f * PASO];

  // banco sobre patas, con ranura y tornillos
  fija.push(sombra(BANCO, -9, P, { pad: 8 }));
  const porProf = (pts) => [...pts].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));
  for (const [x, y] of porProf(k.corners(BANCO, 14))) {
    fija.push(S(k.cylinder(x, y, 6, -9, 1.4, P, 24), { tone: "lo", m: "acero" }));
  }
  fija.push(S(k.slabOf(BANCO, -7.6, 7.6, P, 6, 1.4), { tone: "lo", m: "trabajo" }));
  fija.push(L(k.planOutline(k.insetPlan(BANCO, 5), 0, P, 4), { tone: "faint" }));
  const tornB = k.corners(BANCO, 9);
  fija.push(L(tornB.map(([x, y]) => k.ring(x, y, 2, 0, P, 14)).join(""), { tone: "lo" }));
  fija.push(D(tornB.map(([x, y]) => at([x, y, 0])), { size: 0.5 }));

  // la regla por donde corre la pregunta
  const REGLA = { x: 46, y: -3, w: X0 + 6 * PASO + LADO - 40, d: 8, r: 1 };
  fija.push(S(k.slabOf(REGLA, 0, 0.6, P, 3), { tone: "lo", crease: "none", m: "metal" }));
  const tk = k.topTicks(REGLA.x + 3, REGLA.x + REGLA.w - 3, 4, 5, REGLA.y + 0.8, 0.6, [1.6, 3], P);
  fija.push(L(tk.minor, { tone: "lo" }), L(tk.major, { tone: "mid" }));
  fija.push(D([at([REGLA.x + 1.6, REGLA.y + 4, 0.6]), at([REGLA.x + REGLA.w - 1.6, REGLA.y + 4, 0.6])], { size: 0.45 }));

  // el tablero y sus columnas, de atrás hacia adelante: todas del mismo material (agua), con su
  // tapa de metal; la tapa de la columna que responde se enciende (copia ámbar en la capa viva)
  fija.push(S(k.slabOf(TAB, 0, ZT, P, 3, 0.6), { tone: "mid", m: "metal" }));
  fija.push(L(k.planOutline(k.insetPlan(TAB, 2.5), ZT, P, 2), { tone: "faint" }));
  fija.push(D(k.corners(TAB, 4.5).map(([x, y]) => at([x, y, ZT])), { size: 0.45 }));
  const orden = [...celdas.keys()].sort((a, b) => {
    const [fa, ca] = a.split(",").map(Number), [fb, cb] = b.split(",").map(Number);
    const [xa, ya] = pie(fa, ca), [xb, yb] = pie(fb, cb);
    return k.depthOf([xa + LADO / 2, ya + LADO / 2, 0], P) - k.depthOf([xb + LADO / 2, yb + LADO / 2, 0], P);
  });
  const tapas = [];
  for (const clave of orden) {
    const [f, c] = clave.split(",").map(Number);
    const { n, turno } = celdas.get(clave);
    const [x, y] = pie(f, c);
    const h = alto(n);
    const plan = { x, y, w: LADO, d: LADO, r: 1 };
    fija.push(S(k.slabOf(plan, ZT, h, P, 2, 0.4), { tone: "hi", crease: "lo", m: "agua", inner: L(k.sideSeam(plan, ZT + 2, P, 2), { tone: "faint" }) }));
    const tapa = k.insetPlan(plan, 1.2);
    fija.push(S(k.slabOf(tapa, ZT + h, 1.2, P, 2), { tone: "mid", m: "metal" }));
    if (turno !== undefined) tapas[turno] = S(k.slabOf(tapa, ZT + h, 1.2, P, 2), { tone: "mid", m: "ambar" });
  }

  // la terminal del agente: pie, caja con rejillas, pantalla hacia la barrera y su toma
  fija.push(S(k.slabOf({ x: 0, y: -24, w: 44, d: 44, r: 2 }, 0, 3, P, 3, 0.5), { tone: "mid", m: "acero" }));
  const caja = { x: 2, y: -22, w: 38, d: 40, r: 3 };
  fija.push(S(k.slabOf(caja, 3, 37, P, 4, 1), { tone: "mid", m: "papel", inner: L(k.sideSeam(caja, 8, P, 4), { tone: "faint" }) }));
  const rejas = [];
  for (let q = 0; q < 5; q++) rejas.push(k.planOutline({ x: 8, y: -14 + q * 5, w: 18, d: 2, r: 1 }, 40, P, 3));
  fija.push(L(rejas.join(""), { tone: "lo" }));
  fija.push(D(k.corners(caja, 4).map(([x, y]) => at([x, y, 40])), { size: 0.45 }));
  fija.push(S(k.slabOf({ x: 40, y: -16, w: 1, d: 30, r: 0.4 }, 12, 24, P, 1), { tone: "lo", m: "bosque" }));
  const renglon = (zz, largo) => tramo([41, 11, zz], [41, 11 - largo, zz], P);
  fija.push(L(renglon(32, 20), { tone: "lo", free: true, className: "en-oscuro" }));
  // la respuesta en pantalla: tres renglones que aparecen cuando vuelve
  viva.push(`<g data-v="respuesta" style="opacity:0">${L(renglon(26, 24) + renglon(22, 16) + renglon(18, 21), { tone: "lo", free: true, className: "en-oscuro" })}</g>`);
  const toma = { x: 40, y: -2, w: 1.6, d: 6, r: 0.4 };
  fija.push(S(k.slabOf(toma, 3.4, 4, P, 1), { tone: "lo", m: "bosque" }));
  fija.push(L(k.sideRing([41.6, 1, 5.4], 1, "x", P, 12), { tone: "mid" }));

  // lector de llave antes de la barrera: poste, cabezal con ranura y su piloto
  fija.push(S(k.slabOf({ x: 64, y: -19, w: 8, d: 8, r: 1 }, 0, 1.2, P, 2), { tone: "lo", m: "acero" }));
  fija.push(S(k.cylinder(68, -15, 2.4, 1.2, 18.8, P, 18), { tone: "mid", crease: "none", m: "metal" }));
  fija.push(L(k.sideArc(68, -15, 2.4, 6, P, 14), { tone: "faint" }));
  const lector = { x: 63, y: -20, w: 10, d: 10, r: 1.2 };
  fija.push(S(k.slabOf(lector, 20, 10, P, 2, 0.5), { tone: "mid", m: "papel", inner: L(k.sideSeam(lector, 22, P, 2), { tone: "faint" }) }));
  fija.push(L(k.planOutline({ x: 65, y: -15.6, w: 6, d: 1.2, r: 0.6 }, 30, P, 2), { tone: "lo" }));
  const lLector = lampara([68, -10, 25.4], 2.8, "y", P);
  fija.push(lLector.fija);
  viva.push(lLector.luz("marca-vivo", "lector"));

  // la barrera: caseta con el nombre grabado, poste de apoyo y (en la capa viva) el brazo
  const caseta = { x: 80, y: -30, w: 18, d: 14, r: 1.5 };
  fija.push(S(k.slabOf(caseta, 0, 32, P, 3, 0.8), { tone: "mid", m: "papel", inner: L(k.sideSeam(caseta, 4, P, 3), { tone: "faint" }) }));
  fija.push(L(k.planOutline(k.insetPlan(caseta, 2.5), 32, P, 2), { tone: "faint" }));
  fija.push(D(k.corners(caseta, 1.6).map(([x, y]) => at([x, y, 32])), { size: 0.4 }));
  fija.push(S(k.slabOf({ x: 82, y: -16, w: 14, d: 0.5, r: 0.2 }, 8, 7, P, 1), { tone: "lo", crease: "none", m: "metal" }));
  fija.push(k.faceTextSvg(k.sideMatrix([83.4, -15.5], 10.2, P, "left"), "Terrnova", { size: 2.6, tone: "hi" }));
  // soporte del eje: un buje en la cara de la caseta
  fija.push(S(k.slabOf({ x: 86, y: -16, w: 6, d: 2.5, r: 0.5 }, 22.5, 7.4, P, 1), { tone: "mid", m: "acero" }));
  fija.push(S(k.cylinder(89, 16.6, 1.8, 0, 22.6, P, 16), { tone: "mid", crease: "none", m: "metal" }));
  fija.push(L(k.sideArc(89, 16.6, 1.8, 4, P, 12), { tone: "faint" }));
  fija.push(S(k.slabOf({ x: 86.4, y: 14, w: 5.2, d: 5.2, r: 0.6 }, 22.6, 2.2, P, 2), { tone: "mid", m: "acero" }));

  // el brazo, en el plano x = 89 (coordenadas locales u = y, v = z): gira sobre el eje
  // el brazo tiene canto: cuatro láminas detrás de la cara, corridas en x, forman su grueso
  const CANTO = 1.8;
  const haciaMi = k.towardViewer(P)[0] > 0 ? 1 : -1; // la cara x que mira al lector
  const M = matrizPlano(P, "x", EJE[0] + (haciaMi * CANTO) / 2);
  const [u0, v0] = [EJE[1], EJE[2]];
  const G = 1.3; // medio grueso
  const brazoLocal = [];
  const rect = (a, b, cl) => `<path class="${cl}" d="M${r1(u0 + a)} ${r1(v0 - G)}H${r1(u0 + b)}V${r1(v0 + G)}H${r1(u0 + a)}Z"/>`;
  brazoLocal.push(rect(-1.6, LARGO, "brazo"));
  for (const [a, b] of [[7, 10.5], [15, 18.5], [23, 26.5]]) brazoLocal.push(rect(a, b, "banda"));
  brazoLocal.push(`<path class="brazo-filo" d="M${r1(u0 - 1.6)} ${r1(v0 - G)}H${r1(u0 + LARGO)}V${r1(v0 + G)}H${r1(u0 - 1.6)}Z"/>`);
  const cubo = `<circle class="cubo" cx="${u0}" cy="${v0}" r="2.4"/><circle class="cubo-eje" cx="${u0}" cy="${v0}" r="0.8"/>`;
  for (let c = 4; c >= 1; c--) {
    const Mc = matrizPlano(P, "x", EJE[0] + (haciaMi * CANTO) / 2 - (haciaMi * CANTO * c) / 4);
    viva.push(`<g transform="matrix(${Mc.join(" ")})"><g data-v="brazo${c}">${rect(-1.6, LARGO, c === 4 ? "brazo-canto filo" : "brazo-canto")}</g></g>`);
  }
  viva.push(`<g transform="matrix(${M.join(" ")})"><g data-v="brazo">${brazoLocal.join("")}</g>${cubo}</g>`);

  // el recorrido de la pregunta: por la regla desde la terminal, el lector, la barrera y la columna
  const ZR = 0.6; // cara de la regla
  const A = [49, 1, ZR];
  const tramos = turnos.map((_, i) => {
    const [x] = pie(0, colTurno[i]);
    const cx = x + LADO / 2;
    return [A, [66, 1, ZR], [83.5, 1, ZR], [cx, 1, ZR]];
  });
  // en pantalla, relativo a la ficha armada en A
  const a0 = at(A);
  const recorridos = tramos.map((pts) => pts.map((p) => { const [x, y] = at(p); return [r1(x - a0[0]), r1(y - a0[1])]; }));
  const largos = tramos.map((pts) => pts.slice(1).map((p, j) => Math.hypot(p[0] - pts[j][0], p[1] - pts[j][1])).map(r1));
  const ficha = { x: A[0] - 4, y: A[1] - 4, w: 8, d: 8, r: 2.2 };
  // las fichas aparecen y se van con la escala (un ámbar a medio fundir se ve oliva)
  const [fx, fy] = at([A[0], A[1], ZR + 1.3]);
  const centro = `data-c="${r1(fx)} ${r1(fy)}" style="transform:scale(0);opacity:0"`;
  viva.push(`<g data-v="respuesta-ficha" ${centro}>${S(k.slabOf(ficha, ZR, 2.4, P, 3, 0.4), { tone: "mid", m: "bosque" })}</g>`);
  viva.push(`<g data-v="pregunta" ${centro}>${S(k.slabOf(ficha, ZR, 2.6, P, 3, 0.4), { tone: "mid", m: "ambar" })}</g>`);
  tapas.forEach((t, i) => viva.push(`<g data-v="tapa${i}" style="opacity:0">${t}</g>`));

  return svgDe({
    huella,
    ancho,
    alto: altoV,
    clase: "fig-ruta",
    etiqueta: `Un banco. A la izquierda, la terminal de tu agente; en el medio, el lector de llave y la barrera de Terrnova; a la derecha, un tablero con una columna por cada una de las ${otras.length + turnos.length} entidades, más alta cuantas más fuentes publica. La pregunta corre por la regla, la barrera se levanta, llega a la columna de su entidad (${turnos.map((t) => t.entidad).join(", ")}) y la respuesta vuelve a la terminal.`,
    fija,
    viva,
    vivo: {
      recorridos,
      largos,
      eje: [u0, v0],
      franjas: turnos.map((_, i) => r1(at([pie(0, colTurno[i])[0] + LADO / 2, Y0, ZT])[0])),
      turnos: turnos.map((t) => ({ h: t.herramienta, e: t.entidad, p: t.corta, l: t.licencia, s: t.servido })),
    },
  });
}
