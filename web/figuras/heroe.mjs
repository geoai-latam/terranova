// Figura cero: la maqueta del héroe, el póster de la escena 3D. Los predios reales del SINIC
// alrededor del punto consultado en Santa Marta, sobre una base de maqueta con patas, ranura,
// tornillos, regla en metros de verdad y la flecha del norte grabada; el predio consultado sube
// (teal, el sujeto) y en su techo queda el punto ámbar de la respuesta. La geometría sale de
// web/publico/js/maqueta.js, la misma que dibuja escena-predios.js con three.js, con la misma
// cámara (45°/30°) y la misma rampa de cuatro tonos; así el póster y la escena son una sola imagen.
// Va como <img> (sin CSS de la página): los colores llegan en datos.json desde estilo.css.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import * as M from "../publico/js/maqueta.js";
import { esc, k } from "./comun.mjs";

const AQUI = dirname(fileURLToPath(import.meta.url));
const DATOS_PUB = join(AQUI, "..", "publico", "datos");
// Unidades del viewBox por metro: el póster mide ~1 px por unidad a 1440 px de ancho. Las
// coordenadas van al doble y enteras (medio píxel), en trazos relativos, para que pese poco.
const ESCALA = 1;
const X2 = 2;

// Un trazo compacto: M absoluto y luego l relativo, en enteros del doble.
function trazo(pts, cerrado = true) {
  let out = "";
  let px = 0, py = 0;
  pts.forEach(([x, y], i) => {
    const qx = Math.round(x), qy = Math.round(y);
    if (i === 0) out += `M${qx} ${qy}`;
    else {
      const dx = qx - px, dy = qy - py;
      out += (i === 1 ? "l" : dx < 0 ? "" : " ") + dx + (dy < 0 ? "" : " ") + dy;
    }
    px = qx; py = qy;
  });
  return out + (cerrado ? "z" : "");
}

// El extrude del kit (cuatro tonos por orientación de cara, techo aparte), en puntos: el póster
// junta los trazos de cada predio en pocos <path>.
function losa(anillo, z, alto, P) {
  const area = anillo.reduce((s, [ax, ay], i) => {
    const [bx, by] = anillo[(i + 1) % anillo.length];
    return s + ax * by - bx * ay;
  }, 0);
  const ring = area < 0 ? [...anillo].reverse() : anillo; // antihorario
  const n = ring.length;
  const { sinA, cosA } = k.cameraOf(P);
  const [vx, vy] = k.towardViewer(P);
  const [lx, ly] = [-sinA, cosA];
  const arriba = ring.map(([x, y]) => k.iso([x, y, z + alto], P));
  const abajo = ring.map(([x, y]) => k.iso([x, y, z], P));
  const tonos = [[], [], [], []];
  const borde = [];
  const de = ring.map(([ax, ay], i) => {
    const [bx, by] = ring[(i + 1) % n];
    const L = Math.hypot(bx - ax, by - ay) || 1;
    const nx = (by - ay) / L, ny = -(bx - ax) / L;
    return { nx, ny, ve: nx * vx + ny * vy > 1e-9 };
  });
  const tono = de.map(({ nx, ny }) => Math.min(3, Math.max(0, Math.floor(((nx * lx + ny * ly + 1) / 2) * 4))));
  // Recorre el anillo desde una cara que no se ve: cada tramo de caras vistas da un filo de abajo
  // (una polilínea), dos aristas verticales en sus extremos y, por cada tono seguido, un polígono.
  const ini = de.findIndex((d) => !d.ve);
  if (ini < 0) return { techo: trazo(arriba), tonos: ["", "", "", ""], borde: "" };
  let tramo = [];
  const cierra = () => {
    if (!tramo.length) return;
    const ult = (tramo[tramo.length - 1] + 1) % n;
    const idx = [...tramo, ult];
    borde.push(trazo([arriba[idx[0]], ...idx.map((i) => abajo[i]), arriba[ult]], false));
    // aristas verticales entre dos caras vistas que doblan más de 30° (como EdgesGeometry en 3D)
    for (let m = 1; m < tramo.length; m++) {
      const a = de[tramo[m - 1]], b = de[tramo[m]];
      if (a.nx * b.nx + a.ny * b.ny < Math.cos(Math.PI / 6)) borde.push(trazo([arriba[tramo[m]], abajo[tramo[m]]], false));
    }
    let g = [tramo[0]];
    const sale = () => {
      const fin = (g[g.length - 1] + 1) % n;
      const sup = [...g, fin].map((i) => arriba[i]);
      const inf = [...g, fin].map((i) => abajo[i]).reverse();
      tonos[tono[g[0]]].push(trazo([...sup, ...inf]));
    };
    for (const i of tramo.slice(1)) {
      if (tono[i] === tono[g[0]]) g.push(i);
      else { sale(); g = [i]; }
    }
    sale();
    tramo = [];
  };
  for (let s = 1; s <= n; s++) {
    const i = (ini + s) % n;
    if (de[i].ve) tramo.push(i);
    else cierra();
  }
  cierra();
  return { techo: trazo(arriba), tonos: tonos.map((t) => t.join("")), borde: borde.join("") };
}

const css = (p) => `
.f{fill:${p.fondo}}
.t{fill:${p.e[0]}}.s3{fill:${p.e[1]}}.s2{fill:${p.e[2]}}.s1{fill:${p.e[3]}}.s0{fill:${p.e[4]}}
.l{fill:none;stroke:${p.linea};stroke-width:.6;stroke-linejoin:round;stroke-linecap:round;vector-effect:non-scaling-stroke}
.t.l,.t{stroke:${p.linea};stroke-width:.6;stroke-linejoin:round;vector-effect:non-scaling-stroke}
.u .t{fill:${p.s[0]};stroke:${p.sFilo}}.u .s3{fill:${p.s[1]}}.u .s2{fill:${p.s[2]}}.u .s1{fill:${p.s[3]}}.u .s0{fill:${p.s[4]}}.u .l{stroke:${p.sFilo}}
.iso-fill{fill:${p.fondo}}.iso-shade,.iso-top{stroke:none}
.iso-solid .iso-top{fill:${p.b[0]}}.iso-solid .iso-shade[data-shade="3"]{fill:${p.b[1]}}.iso-solid .iso-shade[data-shade="2"]{fill:${p.b[2]}}.iso-solid .iso-shade[data-shade="1"]{fill:${p.b[3]}}.iso-solid .iso-shade[data-shade="0"]{fill:${p.b[4]}}
.a .iso-top{fill:${p.a[0]}}.a .iso-shade[data-shade="3"]{fill:${p.a[1]}}.a .iso-shade[data-shade="2"]{fill:${p.a[2]}}.a .iso-shade[data-shade="1"]{fill:${p.a[3]}}.a .iso-shade[data-shade="0"]{fill:${p.a[4]}}
.iso-line{fill:none;stroke:${p.linea};stroke-width:.6;stroke-linecap:round;stroke-linejoin:round;vector-effect:non-scaling-stroke}
.iso-line[data-tone="faint"]{stroke:${p.tenue}}.iso-line[data-tone="lo"]{stroke:${p.lo}}.iso-line[data-tone="hi"]{stroke:${p.alta}}
.a .iso-edge{stroke:${p.aFilo}}.a .iso-crease{stroke:${p.aFilo}}
.iso-dots circle{fill:${p.linea}}
.n{fill:${p.b[3]};stroke:${p.lo};stroke-width:.6;vector-effect:non-scaling-stroke}`;

export function heroe(DATOS, HUELLA) {
  const p = DATOS.heroe.paleta;
  const sm = JSON.parse(readFileSync(join(DATOS_PUB, "sm.json"), "utf8"));
  const calles = JSON.parse(readFileSync(join(DATOS_PUB, "calles.json"), "utf8"));
  const Q = M.maqueta(sm, calles);
  const piso = -M.GRUESO - M.PATA.alto;
  const ancho = (by) => ({ x: M.PLACA.x - by, y: M.PLACA.y - by, w: M.PLACA.w + 2 * by, d: M.PLACA.d + 2 * by, r: M.PLACA.r + by });
  const sombra = M.SOMBRA.pasos.map((by) => ancho(by));
  // Encuadre: la base con sus patas y su sombra, y el consultado arriba con su punto.
  const unidad = { origin: [0, 0], scale: ESCALA * X2, azimuth: M.AZIMUT, elevation: M.ELEVACION };
  const caja = [
    ...k.boxCorners(ancho(M.SOMBRA.pasos.at(-1)), piso, 0),
    [Q.consultado.centro[0], Q.consultado.centro[1], M.ALTO + 6],
  ].map((q) => k.iso(q, unidad));
  const kk = k.cameraOf(unidad).k;
  const pad = 14 * X2;
  const xs = caja.map(([x]) => x), ys = caja.map(([, y]) => y);
  const x0 = Math.min(...xs) - pad, x1 = Math.max(...xs) + pad;
  const y0 = Math.min(...ys) - pad, y1 = Math.max(...ys) + pad;
  const W = Math.ceil(x1 - x0), Hh = Math.ceil(y1 - y0);
  const P = { ...unidad, origin: [-x0, -y0] };
  const out = [];

  // Sombra de contacto horneada: la planta de la base, un poco más ancha, en tres escalones de
  // verde translúcido sobre el piso. Sin desenfoque; three.js pinta las mismas tres capas.
  out.push(
    `<g fill="${p.halo}" fill-opacity="${M.SOMBRA.opacidad}">` +
      sombra.map((pl) => `<path d="${k.planOutline(pl, piso, P, 6)}"/>`).join("") +
      "</g>",
  );
  // Patas con brida, de atrás hacia adelante, y la base biselada.
  const patas = k.corners(M.PLACA, M.PATA.dentro).sort((a, b) => k.depthOf([...a, 0], P) - k.depthOf([...b, 0], P));
  for (const [x, y] of patas) {
    out.push(k.solidSvg(k.cylinder(x, y, M.PATA.r + 2.5, piso, 1.6, P, 28), { tone: "lo" }));
    out.push(k.solidSvg(k.cylinder(x, y, M.PATA.r, piso + 1.6, M.PATA.alto - 1.6, P, 28), { tone: "mid" }));
  }
  const ranura = k.insetPlan(M.PLACA, 6);
  out.push(
    k.solidSvg(k.slabOf(M.PLACA, -M.GRUESO, M.GRUESO, P, 6, 1.6), {
      tone: "mid",
      inner: k.lineSvg(k.sideSeam(M.PLACA, -M.GRUESO / 2, P, 6), { tone: "faint" }),
    }),
  );
  out.push(k.lineSvg(k.planOutline(ranura, 0, P, 4), { tone: "faint" }));
  // Tornillos en las esquinas.
  const torn = k.corners(M.PLACA, 11);
  out.push(k.lineSvg(torn.map(([x, y]) => k.ring(x, y, 2.6, 0, P, 16)).join(""), { tone: "lo" }));
  out.push(k.dotsSvg(torn.map(([x, y]) => k.iso([x, y, 0], P)), { size: 0.9 }));
  // Regla del borde delantero izquierdo: una marca cada 10 m y una mayor cada 50 m.
  const G = M.REGLA;
  const tira = { x: G.x0 - 4, y: G.y, w: G.x1 - G.x0 + 8, d: G.ancho, r: 1 };
  out.push(k.solidSvg(k.slabOf(tira, 0, 0.8, P, 2), { tone: "lo", crease: "none" }));
  const marcas = k.topTicks(G.x0, G.x1, G.paso, G.cada, G.y + 0.4, 0.8, [3, 5.5], P);
  out.push(k.lineSvg(marcas.minor, { tone: "lo" }), k.lineSvg(marcas.major, { tone: "mid" }));
  // Flecha del norte grabada (el norte es −y).
  const N = M.NORTE;
  out.push(
    `<path class="n" d="${trazo([
      [N.x, N.y - N.largo],
      [N.x + N.ancho / 2, N.y],
      [N.x, N.y - N.largo * 0.3],
      [N.x - N.ancho / 2, N.y],
    ].map(([x, y]) => k.iso([x, y, 0.05], P)))}"/>`,
  );

  // Predios: todas las caras de lado (un <path> por tono), sus filos y, encima, todos los techos en
  // un solo <path>. Tienen el mismo grosor y no se tocan, así que un techo solo tapa lados de los
  // predios que están detrás: el orden equivale al del pintor y el póster pesa poco.
  const pieza = (s) =>
    s.tonos.map((d, t) => (d ? `<path class="s${t}" d="${d}"/>` : "")).join("") +
    `<path class="l" d="${s.borde}"/><path class="t" d="${s.techo}"/>`;
  const lados = [[], [], [], []], filos = [], techos = [];
  for (const q of Q.predios) {
    const s = losa(q.anillo, 0, M.H, P);
    s.tonos.forEach((d, t) => d && lados[t].push(d));
    filos.push(s.borde);
    techos.push(s.techo);
  }
  out.push(
    lados.map((d, t) => (d.length ? `<path class="s${t}" d="${d.join("")}"/>` : "")).join(""),
    `<path class="l" d="${filos.join("")}"/>`,
    `<path class="t" d="${techos.join("")}"/>`,
  );
  // El consultado, alto y en teal. Los predios que tiene delante y que lo tapan en pantalla se
  // vuelven a pintar encima, de atrás hacia adelante.
  const caja2 = (anillo, alto) => {
    const q = anillo.flatMap(([x, y]) => [k.iso([x, y, 0], P), k.iso([x, y, alto], P)]);
    return [Math.min(...q.map((v) => v[0])), Math.min(...q.map((v) => v[1])), Math.max(...q.map((v) => v[0])), Math.max(...q.map((v) => v[1]))];
  };
  const U = Q.consultado;
  out.push(`<g class="u">${pieza(losa(U.anillo, 0, M.ALTO, P))}</g>`);
  const [ux0, uy0, ux1, uy1] = caja2(U.anillo, M.ALTO);
  const dU = k.depthOf([...U.centro, 0], P);
  Q.predios
    .filter((q) => k.depthOf([...q.centro, 0], P) > dU)
    .filter((q) => {
      const [a0, b0, a1, b1] = caja2(q.anillo, M.H);
      return a0 < ux1 && a1 > ux0 && b0 < uy1 && b1 > uy0;
    })
    .sort((a, b) => k.depthOf([...a.centro, 0], P) - k.depthOf([...b.centro, 0], P))
    .forEach((q) => out.push(pieza(losa(q.anillo, 0, M.H, P))));
  // El punto ámbar de la respuesta, en el techo del consultado.
  const [cx, cy] = Q.consultado.centro;
  out.push(k.solidSvg(k.cylinder(cx, cy, 2.4, M.ALTO, 1.2, P, 20), { tone: "hi", className: "a" }));

  // Rótulos (HTML encima, en % del póster) y el ancla de la línea guía: los usa construir.py.
  const pct = ([x, y]) => [+((x / W) * 100).toFixed(2), +((y / Hh) * 100).toFixed(2)];
  const rotulos = Q.rotulos.map((r) => {
    const a = k.iso([r.x, r.y, M.H], P), b = k.iso([r.x + r.dx, r.y + r.dy, M.H], P);
    let ang = (Math.atan2(b[1] - a[1], b[0] - a[0]) * 180) / Math.PI;
    if (ang > 90) ang -= 180;
    else if (ang < -90) ang += 180;
    return { t: r.t, p: pct(a), a: +ang.toFixed(1) };
  });
  const vivo = {
    rotulos,
    barrio: Q.barrio,
    ancla: pct(k.iso([cx, cy, M.ALTO + 1.2], P)),
    // Para que three.js encuadre igual: dónde cae el centro de la base y cuántas unidades por metro.
    camara: { q: k.iso([0, 0, 0], P).map((v) => +v.toFixed(2)), k: +kk.toFixed(5), w: W, h: Hh },
    codigo: Q.consultado.codigo,
  };
  const etiqueta =
    "Maqueta de los predios reales del barrio " + Q.barrio + ", en Santa Marta, sobre una base con una regla en metros. " +
    "El predio consultado sube cuando llega su respuesta; su altura es simbólica.";
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${Hh}" role="img" aria-label="${esc(etiqueta)}" ` +
    `data-datos="${HUELLA}" data-vivo="${esc(JSON.stringify(vivo))}"><style>${css(p).replace(/\n/g, "")}</style>${out.join("")}</svg>`
  );
}
