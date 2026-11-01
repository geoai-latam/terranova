// Dibuja las dos figuras isométricas de la portada con el kit de Anatomy (kit/iso-kit.mjs, MIT).
//
//   node web/figuras/construir.mjs     # lee datos.json y escribe capas.svg y ruta.svg
//
// Lo que muestran sale de datos.json, que escribe web/construir.py desde el catálogo; su huella
// queda en cada SVG (data-datos) y construir.py se niega a publicar un dibujo viejo. El movimiento
// vive en web/publico/js/figuras.js, que lee data-vivo; sin él, la figura queda armada y quieta.
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import * as k from "./kit/iso-kit.mjs";

const AQUI = dirname(fileURLToPath(import.meta.url));
const crudo = readFileSync(join(AQUI, "datos.json"), "utf8");
// La huella cubre los datos, este script y el kit: construir.py la recalcula igual.
const lf = (f) => readFileSync(join(AQUI, f)).toString("latin1").replace(/\r\n/g, "\n");
const HUELLA = createHash("sha256")
  .update(crudo, "utf8")
  .update(lf("construir.mjs"), "latin1")
  .update(lf("kit/iso-kit.mjs"), "latin1")
  .digest("hex")
  .slice(0, 12);
const DATOS = JSON.parse(crudo);

const S = (paths, style) => k.solidSvg(paths, style);
const L = (d, style) => k.lineSvg(d, style);
const D = (points, style) => k.dotsSvg(points, style);
const r1 = (v) => Math.round(v * 10) / 10;
const esc = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

function svgDe({ ancho, alto, etiqueta, cuerpo, vivo, clase }) {
  const svg = k.figureSvg({ width: ancho, height: alto, label: etiqueta, body: cuerpo, className: clase });
  return svg.replace("<svg ", `<svg data-datos="${HUELLA}" data-vivo="${esc(JSON.stringify(vivo))}" `);
}

// Un rectángulo en el plano de una cara +y (frente), de x0 a x1 y de z0 a z1, a la profundidad y.
const enFrente = (x0, x1, z0, z1, y, P) =>
  k.pathOf([[x0, y, z0], [x1, y, z0], [x1, y, z1], [x0, y, z1]].map((p) => k.iso(p, P)), true);
const tramo = (a, b, P) => k.segment(a, b, P);

// ================================================================ Fig. 1: el bastidor
// Un bastidor de equipos: abajo el módulo de datos (el producto), con un medidor por familia de
// herramientas y tres tomas de salida; encima, tres módulos (Analítica, Automatización, Agentes),
// cada uno con un cable a su toma. Lo que se mueve: los módulos entran al bastidor y el dato sube
// por el cable del módulo encendido.
function capas() {
  const { fuentes, herramientas, familias, modulos } = DATOS.capas;
  const W = 120, FD = 60; // hueco del bastidor: x 0..W, y 0..FD (el frente mira a +y)
  const yF = FD + 1.5; // cara de los frentes
  const UNID = [
    { z: 9, h: 33 },
    { z: 43, h: 22 },
    { z: 66, h: 22 },
    { z: 89, h: 22 },
  ];
  const TECHO = 112;
  const ZOCALO = { x: -9, y: -7, w: W + 18, d: FD + 15, r: 3 };
  const TOMAS = [88, 94, 100]; // x de la toma de cada módulo en el de datos (Analítica, Automatización, Agentes)
  const ENTRA = 30; // cuánto asoma un módulo antes de entrar

  const P = k.fitProjection(
    [...k.boxCorners(ZOCALO, -7, 0), ...k.boxCorners({ x: -4, y: -1, w: W + 8, d: FD + 3 }, TECHO, TECHO + 6)],
    560,
    560,
    { pad: 22, azimuth: 58 },
  );
  const at = (p) => k.iso(p, P);
  const out = [];

  // zócalo sobre patas, con ranura, tornillos y regla en el borde delantero
  out.push(`<path class="iso-halo" d="${k.haloOf(ZOCALO, -7, 15, P)}"/>`);
  const porProf = (pts) => [...pts].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));
  for (const [x, y] of porProf(k.corners(ZOCALO, 9))) {
    out.push(S(k.cylinder(x, y, 5.6, -7, 1.4, P, 24), { tone: "lo" }));
    out.push(S(k.cylinder(x, y, 4.2, -5.6, 5.6, P, 24), { tone: "mid" }));
  }
  out.push(S(k.slabOf(ZOCALO, 0, 8, P, 6, 1.2), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(ZOCALO, 3.5), 8, P, 4), { tone: "faint" }));
  const tornZ = k.corners(ZOCALO, 6);
  out.push(L(tornZ.map(([x, y]) => k.ring(x, y, 1.6, 8, P, 14)).join(""), { tone: "lo" }));
  out.push(D(tornZ.map(([x, y]) => at([x, y, 8])), { size: 0.45 }));
  const regla = { x: 8, y: ZOCALO.y + ZOCALO.d - 3.4, w: W - 16, d: 2.6, r: 0.6 };
  out.push(S(k.slabOf(regla, 8, 0.5, P, 2), { tone: "lo", crease: "none" }));
  const marcas = k.topTicks(regla.x + 2, regla.x + regla.w - 2, 4, 5, regla.y + 2.6, 8.5, [-1, -1.8], P);
  out.push(L(marcas.minor, { tone: "lo" }), L(marcas.major, { tone: "mid" }));

  // estructura de atrás: panel izquierdo y los dos rieles delanteros
  out.push(S(k.slabOf({ x: -3, y: 0, w: 3, d: yF, r: 0.5 }, 8, TECHO - 8, P, 2), { tone: "mid" }));
  for (const x of [0, W - 7]) {
    const riel = { x, y: FD - 7, w: 7, d: 6, r: 0.4 };
    const agujeros = [];
    for (let z = 12; z < TECHO - 2; z += 4.6) agujeros.push(at([x + 3.5, FD - 1, z]));
    out.push(S(k.slabOf(riel, 8, TECHO - 8, P, 2), { tone: "mid" }));
    out.push(D(agujeros, { size: 0.42, tone: "lo" }));
  }

  // los módulos, de abajo arriba; cada uno en su grupo para entrar desde el frente
  const nombres = ["Datos", ...modulos.map((m) => m.nombre)];
  const zToma = [];
  UNID.forEach(({ z, h }, i) => {
    const g = [];
    const tope = z + h;
    g.push(S(k.slabOf({ x: 7, y: 2, w: W - 14, d: FD - 3, r: 0.6 }, z + 0.5, h - 1, P, 2, 0.4), { tone: "lo" }));
    const frente = { x: 0.5, y: FD - 1, w: W - 1, d: 2.5, r: 0.5 };
    const costura = k.sideSeam(frente, z + 1.6, P, 2);
    g.push(
      `<g data-frente>${S(k.slabOf(frente, z, h, P, 2, 0.5), { tone: i === 0 ? "hi" : "mid", inner: L(costura, { tone: "faint" }) })}</g>`,
    );
    // orejas con dos tornillos por lado
    const torn = [];
    for (const x of [3.6, W - 3.6]) for (const zz of [z + 4.5, tope - 4.5]) torn.push([x, yF, zz]);
    g.push(L(torn.map((p) => k.sideRing(p, 1.3, "y", P, 14)).join(""), { tone: "lo" }));
    g.push(D(torn.map(at), { size: 0.42 }));
    // asas verticales junto a las orejas
    for (const x of [7.6, W - 10.1]) {
      g.push(S(k.slabOf({ x, y: yF, w: 2.5, d: 1.6, r: 0.3 }, z + 4, 2, P, 1), { tone: "mid", crease: "none" }));
      g.push(S(k.slabOf({ x, y: yF, w: 2.5, d: 1.6, r: 0.3 }, tope - 6, 2, P, 1), { tone: "mid", crease: "none" }));
      g.push(S(k.slabOf({ x, y: yF + 1.6, w: 2.5, d: 2.2, r: 0.6 }, z + 4, h - 8, P, 2), { tone: "mid" }));
    }
    // placa de rótulo: solo el módulo de datos lleva texto grabado; los demás, tres renglones
    g.push(S(k.slabOf({ x: 14, y: yF, w: 20, d: 0.6, r: 0.3 }, tope - 10, 6.4, P, 1), { tone: "lo", crease: "none" }));
    if (i === 0) {
      g.push(k.faceTextSvg(k.sideMatrix([15.4, yF + 0.6], tope - 5.2, P, "left"), "Datos", { size: 3.6, tone: "hi" }));
      g.push(k.faceTextSvg(k.sideMatrix([15.4, yF + 0.6], tope - 15.2, P, "left"), `${fuentes} fuentes`, { size: 2.4, tone: "mid" }));
    } else {
      const reng = [17, 12, 14].map((largo, j) => tramo([15.6, yF + 0.6, tope - 5.4 - j * 1.6], [15.6 + largo, yF + 0.6, tope - 5.4 - j * 1.6], P));
      g.push(L(reng.join(""), { tone: "lo", free: true }));
    }
    const ventana = (x0, x1, z0, z1) => S(k.slabOf({ x: x0, y: yF, w: x1 - x0, d: 0.5, r: 0.3 }, z0, z1 - z0, P, 1), { tone: "lo", className: "oscuro", crease: "none" });
    const tomaEn = (cx, zc) => {
      g.push(S(k.slabOf({ x: cx - 2.2, y: yF, w: 4.4, d: 0.7, r: 0.3 }, zc - 3, 6, P, 1), { tone: "lo", className: "oscuro" }));
      g.push(L(k.sideRing([cx, yF + 0.7, zc], 1.1, "y", P, 12), { tone: "mid" }));
    };
    if (i === 0) {
      // un medidor por familia: ocho luces, encendidas en proporción a sus herramientas
      const mayor = Math.max(...familias.map(([, n]) => n));
      familias.forEach(([nombre, n], j) => {
        const x0 = 38 + j * 6.6;
        g.push(ventana(x0, x0 + 4.6, z + 6, z + 29));
        const luces = Math.max(1, Math.round((n / mayor) * 8));
        const pts = Array.from({ length: 8 }, (_, q) => at([x0 + 2.3, yF + 0.5, z + 8.4 + q * 2.6]));
        g.push(`<g class="medidor" data-familia="${esc(nombre)}" data-n="${n}">`);
        g.push(`<g class="luz-on">${D(pts.slice(0, luces), { size: 0.62, tone: "hi" })}</g>`);
        g.push(`<g class="luz-off">${D(pts.slice(luces), { size: 0.5, tone: "faint" })}</g></g>`);
      });
      for (const cx of TOMAS) tomaEn(cx, z + 18);
      // interruptor y piloto
      g.push(S(k.slabOf({ x: 103.4, y: yF, w: 2.6, d: 1.4, r: 0.4 }, z + 14, 6, P, 1), { tone: "mid" }));
      g.push(D([at([104.7, yF, z + 24.5])], { size: 0.6, tone: "hi" }));
      zToma.push(z + 18);
    } else {
      const cx = TOMAS[i - 1];
      if (i === 1) {
        // Analítica: una ventana con la rejilla de una tabla
        g.push(ventana(40, 78, z + 4, tope - 4));
        const filas = [z + 8.5, z + 12.5, tope - 8.5].map((zz) => tramo([40, yF + 0.5, zz], [78, yF + 0.5, zz], P));
        const cols = [52, 64].map((xx) => tramo([xx, yF + 0.5, z + 4], [xx, yF + 0.5, tope - 4], P));
        g.push(L(filas.join("") + cols.join(""), { tone: "lo", className: "en-oscuro" }));
      } else if (i === 2) {
        // Automatización: seis pilotos de tareas con su bisel y una ranura de lectura
        const pil = Array.from({ length: 6 }, (_, q) => [42 + q * 6, yF, z + 14]);
        g.push(L(pil.map((p) => k.sideRing(p, 1.5, "y", P, 14)).join(""), { tone: "lo" }));
        g.push(D(pil.map(at), { size: 0.55, tone: "mid" }));
        g.push(ventana(42, 72, z + 5, z + 9));
      } else {
        // Agentes: una pantalla con tres renglones de texto
        g.push(ventana(40, 80, z + 4, tope - 4));
        const reng = [30, 22, 26].map((largo, j) => tramo([42.5, yF + 0.5, tope - 7.5 - j * 3.6], [42.5 + largo, yF + 0.5, tope - 7.5 - j * 3.6], P));
        g.push(L(reng.join(""), { tone: "lo", free: true, className: "en-oscuro" }));
      }
      tomaEn(cx, z + h / 2);
      zToma.push(z + h / 2);
    }
    out.push(`<g data-modulo="${i}" data-nombre="${esc(nombres[i])}">${g.join("")}</g>`);
  });

  // panel derecho con rejillas de ventilación (ranuras cerradas) y el techo
  const panel = { x: W, y: 0, w: 3, d: yF, r: 0.5 };
  const rejillas = [];
  for (let fila = 0; fila < 5; fila++) {
    const zz = 22 + fila * 16;
    for (const [y0, y1] of [[8, 26], [32, 50]]) {
      rejillas.push(k.pathOf([[W + 3, y0, zz], [W + 3, y1, zz], [W + 3, y1, zz + 2.2], [W + 3, y0, zz + 2.2]].map(at), true));
    }
  }
  out.push(S(k.slabOf(panel, 8, TECHO - 8, P, 2), { tone: "mid", inner: L(rejillas.join(""), { tone: "lo" }) }));
  const techo = { x: -4, y: -1, w: W + 8, d: FD + 3, r: 1.5 };
  out.push(S(k.slabOf(techo, TECHO, 6, P, 3, 0.8), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(techo, 3), TECHO + 6, P, 2), { tone: "faint" }));
  const tornT = k.corners(techo, 5.5);
  out.push(D(tornT.map(([x, y]) => at([x, y, TECHO + 6])), { size: 0.45 }));

  // cables: de la toma de cada módulo a su toma en el de datos, por delante de los frentes
  const yC = yF + 2.4;
  const cables = [];
  const vivoCables = [];
  modulos.forEach((m, j) => {
    const cx = TOMAS[j];
    const arriba = zToma[j + 1] - 2.4;
    const abajo = zToma[0] + 2.4;
    const puntos = [[cx, yC, arriba], [cx, yC, abajo]].map(at);
    const d = k.pathOf(puntos);
    const clavija = (zc) => S(k.slabOf({ x: cx - 1.7, y: yF + 0.7, w: 3.4, d: 3.4, r: 0.6 }, zc - 2.4, 4.8, P, 2), { tone: "mid" });
    cables.push(
      `<g class="cable" data-cable="${j + 1}">${clavija(zToma[j + 1])}${clavija(zToma[0])}` +
        `<path class="cable-forro" d="${d}"/><path class="cable-alma" d="${d}"/>` +
        `<path class="cable-pulso" pathLength="100" d="${k.pathOf([...puntos].reverse())}"/></g>`,
    );
    vivoCables.push(j + 1);
  });
  out.push(`<g class="cables">${cables.join("")}</g>`);

  const ent = k.axisVector(P, [0, ENTRA, 0]);
  const lecturas = [
    `Datos · ${fuentes} fuentes · ${herramientas} herramientas`,
    ...modulos.map((m) => `${m.nombre} · conectado por ${m.puerta}`),
  ];
  // franjas de pantalla de cada módulo, para elegir con el puntero (de arriba abajo)
  const franjas = UNID.map(({ z, h }) => {
    const [, y0] = at([W / 2, yF, z + h]);
    const [, y1] = at([W / 2, yF, z]);
    return [r1(y0), r1(y1)];
  });
  return svgDe({
    ancho: 560,
    alto: 560,
    clase: "fig-capas",
    etiqueta: `Un bastidor de equipos. Abajo, el módulo de datos con ${fuentes} fuentes: un medidor por cada una de las ${familias.length} familias de herramientas, encendido según cuántas tiene, y tres tomas. Encima, ${modulos.map((m) => `${m.nombre} (${m.puerta})`).join(", ")}, cada uno con un cable a su toma.`,
    cuerpo: out,
    vivo: { entra: ent.map(r1), lecturas, franjas, cables: vivoCables },
  });
}

// ================================================================ Fig. 2: la ruta de una pregunta
// Un banco: la terminal del agente, un lector de llave, una barrera con el nombre de Terrnova y un
// tablero con una columna por entidad (alta según sus fuentes). La pregunta corre por una regla
// desde la terminal, la barrera se levanta, llega a la columna de su entidad y vuelve.
function ruta() {
  const { turnos, otras } = DATOS.ruta;
  const BANCO = { x: -14, y: -144, w: 296, d: 166, r: 4 };
  const TAB = { x: 104, y: -130, w: 168, d: 124, r: 2 };
  const PASO = 19.5, LADO = 13, X0 = 111, Y0 = -20; // columna (fila 0, col 0): x X0..X0+LADO, y Y0..Y0+LADO
  const COLS = 8, FILAS = 6;
  const alto = (n) => 6 + 1.9 * n;
  const P = k.fitProjection(
    [...k.boxCorners(BANCO, -9, 0), [X0, Y0 - 5 * PASO, 4 + alto(34)], [89, -16, 70], [0, -24, 42]],
    720,
    440,
    { pad: 20, azimuth: 45 },
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
  out.push(S(k.slabOf(REGLA, 0, 0.6, P, 3), { tone: "lo", crease: "none" }));
  const tk = k.topTicks(REGLA.x + 3, REGLA.x + REGLA.w - 3, 4, 5, REGLA.y + 0.8, 0.6, [1.6, 3], P);
  out.push(L(tk.minor, { tone: "lo" }), L(tk.major, { tone: "mid" }));
  out.push(D([at([REGLA.x + 1.6, REGLA.y + 4, 0.6]), at([REGLA.x + REGLA.w - 1.6, REGLA.y + 4, 0.6])], { size: 0.45 }));

  // el tablero y sus columnas, de atrás hacia adelante
  out.push(S(k.slabOf(TAB, 0, 4, P, 3, 0.6), { tone: "mid" }));
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
    const cuerpo = S(k.slabOf(plan, 4, h, P, 2, 0.4), { tone: turno === undefined ? "mid" : "hi", crease: "lo" });
    out.push(turno === undefined ? cuerpo + tapa : `<g data-columna="${turno}">${cuerpo}${tapa}</g>`);
  }

  // la terminal del agente: pie, caja con rejillas, pantalla hacia la barrera y su toma
  out.push(S(k.slabOf({ x: 0, y: -24, w: 44, d: 44, r: 2 }, 0, 3, P, 3, 0.5), { tone: "mid" }));
  const caja = { x: 2, y: -22, w: 38, d: 40, r: 3 };
  out.push(S(k.slabOf(caja, 3, 37, P, 4, 1), { tone: "mid", inner: L(k.sideSeam(caja, 8, P, 4), { tone: "faint" }) }));
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
  out.push(S(k.cylinder(68, -15, 2.4, 0, 20, P, 18), { tone: "mid", crease: "none" }));
  const lector = { x: 63, y: -20, w: 10, d: 10, r: 1.2 };
  out.push(S(k.slabOf(lector, 20, 7, P, 2, 0.5), { tone: "mid" }));
  out.push(L(k.planOutline({ x: 65, y: -15.6, w: 6, d: 1.2, r: 0.6 }, 27, P, 2), { tone: "lo" }));
  out.push(`<g data-piloto>${D([at([71, -10, 24.5])], { size: 0.7, tone: "hi" })}</g>`);

  // la barrera: caseta con el nombre, poste de apoyo y (después) el brazo
  const caseta = { x: 80, y: -30, w: 18, d: 14, r: 1.5 };
  out.push(S(k.slabOf(caseta, 0, 32, P, 3, 0.8), { tone: "mid", inner: L(k.sideSeam(caseta, 4, P, 3), { tone: "faint" }) }));
  out.push(L(k.planOutline(k.insetPlan(caseta, 2.5), 32, P, 2), { tone: "faint" }));
  out.push(k.faceTextSvg(k.sideMatrix([81.8, -16], 13, P, "left"), "Terrnova", { size: 3.2, tone: "hi" }));
  out.push(S(k.slabOf({ x: 86, y: -16, w: 6, d: 2.2, r: 0.4 }, 22.5, 7.6, P, 1), { tone: "lo" }));
  out.push(S(k.cylinder(89, 16.6, 1.8, 0, 22.6, P, 16), { tone: "mid", crease: "none" }));
  out.push(S(k.slabOf({ x: 86.4, y: 14, w: 5.2, d: 5.2, r: 0.6 }, 22.6, 2.2, P, 2), { tone: "mid" }));

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
    ancho: 720,
    alto: 440,
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

function casco(pts) {
  const p = [...pts].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cruz = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const bajo = [], alto = [];
  for (const q of p) {
    while (bajo.length >= 2 && cruz(bajo[bajo.length - 2], bajo[bajo.length - 1], q) <= 0) bajo.pop();
    bajo.push(q);
  }
  for (const q of p.reverse()) {
    while (alto.length >= 2 && cruz(alto[alto.length - 2], alto[alto.length - 1], q) <= 0) alto.pop();
    alto.push(q);
  }
  return bajo.slice(0, -1).concat(alto.slice(0, -1));
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  writeFileSync(join(AQUI, "capas.svg"), capas() + "\n");
  writeFileSync(join(AQUI, "ruta.svg"), ruta() + "\n");
  console.log(`figuras escritas (datos ${HUELLA})`);
}
