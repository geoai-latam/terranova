// Fig. ruta: un banco con la terminal del agente, un lector de llave, una barrera con el nombre de
// Terrnova y un tablero con una columna por entidad (alta según sus fuentes). La pregunta corre por
// una regla desde la terminal, la barrera se levanta, llega a la columna de su entidad y vuelve.
import { D, L, S, casco, encuadre, k, r1, svgDe } from "./comun.mjs";

const tramo = (a, b, P) => k.segment(a, b, P);

export function ruta(DATOS, huella) {
  const { turnos, otras } = DATOS.ruta;
  const BANCO = { x: -14, y: -144, w: 296, d: 166, r: 4 };
  const TAB = { x: 104, y: -130, w: 168, d: 124, r: 2 };
  const PASO = 19.5, LADO = 13, X0 = 111, Y0 = -20; // columna (fila 0, col 0): x X0..X0+LADO, y Y0..Y0+LADO
  const COLS = 8, FILAS = 6;
  const alto = (n) => 6 + 1.9 * n;
  const { P, ancho, alto: altoV } = encuadre(
    [...k.boxCorners(BANCO, -16, 0), [X0, Y0 - 5 * PASO, 4 + alto(34)], [89, -16, 70], [0, -24, 42]],
    { azimuth: 45 },
  );
  const at = (p) => k.iso(p, P);
  const out = [];

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
  const base = (f, c) => [X0 + c * PASO, Y0 - f * PASO];

  // banco sobre patas
  out.push(`<path class="iso-halo" d="${k.haloOf(BANCO, -9, 9, P)}"/>`);
  const porProf = (pts) => [...pts].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));
  for (const [x, y] of porProf(k.corners(BANCO, 14))) {
    out.push(S(k.cylinder(x, y, 6, -9, 1.4, P, 24), { tone: "lo" }));
  }
  out.push(S(k.slabOf(BANCO, -7.6, 7.6, P, 6, 1.4), { tone: "lo" }));
  out.push(L(k.planOutline(k.insetPlan(BANCO, 5), 0, P, 4), { tone: "faint" }));
  const tornB = k.corners(BANCO, 9);
  out.push(L(tornB.map(([x, y]) => k.ring(x, y, 2, 0, P, 14)).join(""), { tone: "lo" }));
  out.push(D(tornB.map(([x, y]) => at([x, y, 0])), { size: 0.5 }));

  // la regla por donde corre la pregunta
  const REGLA = { x: 46, y: -3, w: X0 + 6 * PASO + LADO - 40, d: 8, r: 1 };
  out.push(S(k.slabOf(REGLA, 0, 0.6, P, 3), { tone: "lo", crease: "none", m: "ocre" }));
  const tk = k.topTicks(REGLA.x + 3, REGLA.x + REGLA.w - 3, 4, 5, REGLA.y + 0.8, 0.6, [1.6, 3], P);
  out.push(L(tk.minor, { tone: "lo" }), L(tk.major, { tone: "mid" }));
  out.push(D([at([REGLA.x + 1.6, REGLA.y + 4, 0.6]), at([REGLA.x + REGLA.w - 1.6, REGLA.y + 4, 0.6])], { size: 0.45 }));

  // el tablero y sus columnas, de atrás hacia adelante
  out.push(S(k.slabOf(TAB, 0, 4, P, 3, 0.6), { tone: "mid", m: "bosque" }));
  out.push(L(k.planOutline(k.insetPlan(TAB, 2.5), 4, P, 2), { tone: "faint" }));
  out.push(D(k.corners(TAB, 4.5).map(([x, y]) => at([x, y, 4])), { size: 0.45 }));
  const orden = [...celdas.keys()].sort((a, b) => {
    const [fa, ca] = a.split(",").map(Number), [fb, cb] = b.split(",").map(Number);
    const [xa, ya] = base(fa, ca), [xb, yb] = base(fb, cb);
    return k.depthOf([xa + LADO / 2, ya + LADO / 2, 0], P) - k.depthOf([xb + LADO / 2, yb + LADO / 2, 0], P);
  });
  for (const clave of orden) {
    const [f, c] = clave.split(",").map(Number);
    const { n, turno } = celdas.get(clave);
    const [x, y] = base(f, c);
    const h = alto(n);
    const plan = { x, y, w: LADO, d: LADO, r: 1 };
    const tapa = L(k.planOutline(k.insetPlan(plan, 2), 4 + h, P, 2), { tone: "faint" });
    const cuerpo = S(k.slabOf(plan, 4, h, P, 2, 0.4), { tone: turno === undefined ? "mid" : "hi", crease: "lo", m: turno === undefined ? "teal" : "agua" });
    // en las demás columnas, un piloto en la tapa que titila a su ritmo: cada entidad responde
    const q = (f * 7 + c * 3) % 11;
    const chispa = `<g class="parpadea piloto-claro" style="--p:${(1.6 + q * 0.23).toFixed(2)}s;--d:-${(q * 0.37).toFixed(2)}s">${D([at([x + LADO / 2, y + LADO / 2, 4 + h])], { size: 0.9, tone: "hi" })}</g>`;
    out.push(turno === undefined ? cuerpo + tapa + chispa : `<g data-columna="${turno}">${cuerpo}${tapa}</g>`);
  }

  // la terminal del agente: pie, caja con rejillas, pantalla hacia la barrera y su toma
  out.push(S(k.slabOf({ x: 0, y: -24, w: 44, d: 44, r: 2 }, 0, 3, P, 3, 0.5), { tone: "mid", m: "bosque" }));
  const caja = { x: 2, y: -22, w: 38, d: 40, r: 3 };
  out.push(S(k.slabOf(caja, 3, 37, P, 4, 1), { tone: "mid", m: "papel", inner: L(k.sideSeam(caja, 8, P, 4), { tone: "faint" }) }));
  const rejas = [];
  for (let q = 0; q < 5; q++) rejas.push(k.planOutline({ x: 8, y: -14 + q * 5, w: 18, d: 2, r: 1 }, 40, P, 3));
  out.push(L(rejas.join(""), { tone: "lo" }));
  out.push(D(k.corners(caja, 4).map(([x, y]) => at([x, y, 40])), { size: 0.45 }));
  out.push(S(k.slabOf({ x: 40, y: -16, w: 1, d: 30, r: 0.4 }, 12, 24, P, 1), { tone: "lo", className: "oscuro" }));
  const renglon = (zz, largo) => tramo([41, 11, zz], [41, 11 - largo, zz], P);
  out.push(L(renglon(32, 20), { tone: "lo", free: true, className: "en-oscuro" }));
  const respuestas = turnos.map(
    (_, i) => `<g data-respuesta="${i}">${L(renglon(26, 24) + renglon(22, 16) + renglon(18, 21), { tone: "lo", free: true, className: "en-oscuro" })}</g>`,
  );
  out.push(respuestas.join(""));
  out.push(S(k.slabOf({ x: 40, y: -2, w: 1.2, d: 6, r: 0.4 }, 3.4, 4, P, 1), { tone: "lo", className: "oscuro" }));

  // lector de llave antes de la barrera
  out.push(S(k.cylinder(68, -15, 2.4, 0, 20, P, 18), { tone: "mid", crease: "none", m: "acero" }));
  const lector = { x: 63, y: -20, w: 10, d: 10, r: 1.2 };
  out.push(S(k.slabOf(lector, 20, 7, P, 2, 0.5), { tone: "mid", m: "ocre" }));
  out.push(L(k.planOutline({ x: 65, y: -15.6, w: 6, d: 1.2, r: 0.6 }, 27, P, 2), { tone: "lo" }));
  out.push(`<g data-piloto>${D([at([71, -10, 24.5])], { size: 0.8, tone: "hi" })}</g>`);

  // la barrera: caseta con el nombre, poste de apoyo y (después) el brazo
  const caseta = { x: 80, y: -30, w: 18, d: 14, r: 1.5 };
  out.push(S(k.slabOf(caseta, 0, 32, P, 3, 0.8), { tone: "mid", m: "verde", inner: L(k.sideSeam(caseta, 4, P, 3), { tone: "faint" }) }));
  out.push(L(k.planOutline(k.insetPlan(caseta, 2.5), 32, P, 2), { tone: "faint" }));
  out.push(`<g class="texto-claro">${k.faceTextSvg(k.sideMatrix([81.8, -16], 13, P, "left"), "Terrnova", { size: 3.2, tone: "hi" })}</g>`);
  out.push(S(k.slabOf({ x: 86, y: -16, w: 6, d: 2.2, r: 0.4 }, 22.5, 7.6, P, 1), { tone: "lo", m: "ocre" }));
  out.push(S(k.cylinder(89, 16.6, 1.8, 0, 22.6, P, 16), { tone: "mid", crease: "none", m: "acero" }));
  out.push(S(k.slabOf({ x: 86.4, y: 14, w: 5.2, d: 5.2, r: 0.6 }, 22.6, 2.2, P, 2), { tone: "mid", m: "ocre" }));

  // el recorrido de cada turno: de la toma de la terminal por la regla hasta la columna
  const recorridos = turnos.map((_, i) => {
    const [x] = base(0, colTurno[i]);
    const cx = x + LADO / 2;
    return [[41.2, 1, 5.4], [46, 1, 0.6], [cx, 1, 0.6], [cx, -3, 0.6], [cx, -3.6, 4], [cx, Y0 + LADO, 4]].map(at).map(([a, b]) => [r1(a), r1(b)]);
  });
  recorridos.forEach((pts, i) => {
    out.push(`<path class="traza" data-traza="${i}" pathLength="100" d="${k.pathOf(pts)}"/>`);
  });
  out.push(`<circle class="pregunta" data-pregunta-punto r="2.2" cx="${recorridos[0][0][0]}" cy="${recorridos[0][0][1]}"/>`);

  // el brazo, dibujado abajo; figuras.js lo rehace en cada cuadro al girar sobre su eje x
  const BRAZO = { eje: [89, -16, 26.2], largo: 32.6, ancho: 3, grueso: 2.6, bandas: [[8, 12], [17, 21], [26, 30]] };
  const brazo = brazoSvg(BRAZO, 0, P);
  out.push(`<g data-brazo>${brazo}</g>`);

  return svgDe({
    huella,
    ancho,
    alto: altoV,
    clase: "fig-ruta",
    etiqueta: `Un banco. A la izquierda, la terminal de tu agente; en el medio, el lector de llave y la barrera de Terrnova; a la derecha, un tablero con una columna por cada una de las ${otras.length + turnos.length} entidades, más alta cuantas más fuentes publica. La pregunta corre por la regla, la barrera se levanta, llega a la columna de su entidad (${turnos.map((t) => t.entidad).join(", ")}) y vuelve con la respuesta.`,
    cuerpo: out,
    vivo: {
      P,
      brazo: BRAZO,
      recorridos,
      turnos: turnos.map((t) => ({ h: t.herramienta, e: t.entidad, p: t.pregunta, l: t.licencia, s: t.servido })),
    },
  });
}

// El brazo de la barrera a un ángulo (0 = bajado, en grados): un prisma con tres bandas. La misma
// cuenta está en figuras.js; aquí se dibuja la pose de reposo.
export function brazoSvg({ eje, largo, ancho, grueso, bandas }, grados, P) {
  const t = (grados * Math.PI) / 180;
  const dir = [0, Math.cos(t), Math.sin(t)];
  const nor = [0, -Math.sin(t), Math.cos(t)];
  const pt = (s, a, g) => [eje[0] + a, eje[1] + dir[1] * s + nor[1] * g, eje[2] + dir[2] * s + nor[2] * g];
  const prisma = (s0, s1, cl) => {
    const esquinas = [];
    for (const s of [s0, s1]) for (const a of [-ancho / 2, ancho / 2]) for (const g of [-grueso / 2, grueso / 2]) esquinas.push(k.iso(pt(s, a, g), P));
    return `<path class="${cl}" d="${k.pathOf(casco(esquinas), true)}"/>`;
  };
  const arriba = k.pathOf([pt(0, -ancho / 2, grueso / 2), pt(largo, -ancho / 2, grueso / 2), pt(largo, ancho / 2, grueso / 2)].map((p) => k.iso(p, P)));
  return prisma(0, largo, "brazo") + bandas.map(([a, b]) => prisma(a, b, "banda")).join("") + `<path class="brazo-arista" d="${arriba}"/>`;
}
