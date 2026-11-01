// Lo común a todas las figuras: la misma cámara (elevación 30°), la misma escala de pantalla, el
// mismo grosor de línea (lo pone el CSS) y las mismas piezas de banco (base sobre patas, regla,
// tornillos y placa). Cada figura vive en su módulo y construir.mjs las escribe todas.
import * as k from "./kit/iso-kit.mjs";

export { k };
// Cada pieza lleva un material de la paleta (m: "papel", "metal", "trabajo", "acero" para la
// estructura; "teal", "agua", "ocre", sus "-fuerte" o "bosque" para el sujeto; "ambar" para la pieza
// que está pasando; ver estilo.css). Sin material explícito: la base (lo) en superficie de trabajo,
// la estructura (mid) en metal y el resto (hi) en papel.
const POR_TONO = { lo: "trabajo", mid: "metal", hi: "papel" };
export const S = (paths, style = {}) => {
  const { m, className, ...resto } = style;
  const mat = m ?? POR_TONO[style.tone ?? "hi"];
  return k.solidSvg(paths, { ...resto, className: `m-${mat}${className ? ` ${className}` : ""}` });
};
export const L = (d, style) => k.lineSvg(d, style);
export const D = (points, style) => k.dotsSvg(points, style);
export const r1 = (v) => Math.round(v * 10) / 10;
export const esc = (t) =>
  String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// Escala común: píxeles del viewBox por unidad de mundo. Todas las figuras se dibujan con ella,
// así una tuerca mide lo mismo en todas; el ancho del viewBox sale de lo que ocupa cada objeto.
export const ESCALA = 2.1;

// Cámara a escala fija: proyecta las esquinas, mide la caja y pone el origen con un margen.
export function encuadre(puntos, { azimuth = 45, pad = 10, escala = ESCALA } = {}) {
  const unidad = { origin: [0, 0], scale: escala, azimuth, elevation: 30 };
  const plano = puntos.map((p) => k.iso(p, unidad));
  const xs = plano.map(([x]) => x), ys = plano.map(([, y]) => y);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const ancho = Math.ceil(x1 - x0 + pad * 2), alto = Math.ceil(y1 - y0 + pad * 2);
  return { P: { origin: [pad - x0, pad - y0], scale: escala, azimuth, elevation: 30 }, ancho, alto };
}

// El SVG de una figura en dos capas, en dos archivos: la fija (todo lo que no se mueve), que la
// página muestra como <img> (sin DOM: no cuesta estilo ni diseño al desplazarse), y la viva (las
// piezas que se mueven, lo que las tapa y los rótulos grabados, que necesitan la fuente del sitio),
// que figuras.js pone encima, en línea. data-vivo lleva lo que el movimiento necesita.
// La capa fija se parte en trozos de a lo sumo PIEZAS_POR_TROZO elementos (un trazo largo cuenta
// por su largo), en orden de pintura:
// cada trozo es una imagen y el navegador lee cada una en su propia tarea (una sola de 900 trazos
// pasaba de 40 ms a CPU 4×). Las imágenes van una sobre otra, en el mismo orden.
const PIEZAS_POR_TROZO = 170;
const piezas = (t) => (t.match(/<(path|circle|text|line|ellipse|rect|polygon)\b/g) || []).length;
export function svgDe({ huella, ancho, alto, etiqueta, fija, cuerpo: viejo, viva = [], vivo, clase }) {
  if (fija === undefined) fija = viejo;
  // los rótulos grabados (texto) van en la viva: un SVG en <img> no ve las fuentes de la página
  const textos = [];
  const sinTexto = [].concat(fija).map((t) => t.replace(/<text class="iso-face-text"[^>]*>[^<]*<\/text>/g, (x) => (textos.push(x), "")));
  const trozos = [[]];
  let n = 0;
  for (const t of sinTexto) {
    const m = piezas(t) + Math.floor(t.length / 500); // un trazo muy largo también pesa
    if (n && n + m > PIEZAS_POR_TROZO) { trozos.push([]); n = 0; }
    trozos[trozos.length - 1].push(t);
    n += m;
  }
  const fijas = trozos.map((tr, i) =>
    k.figureSvg({ width: ancho, height: alto, label: i === 0 ? etiqueta : "", body: `<g class="capa-fija">${tr.join("")}</g>`, className: clase })
      .replace("<svg ", `<svg data-datos="${huella}"${i === 0 ? ` data-trozos="${trozos.length}"` : ""} `),
  );
  const capaViva = k.figureSvg({ width: ancho, height: alto, label: "", body: `<g class="capa-viva">${textos.join("")}${[].concat(viva).join("")}</g>`, className: `${clase} capa-viva-svg` })
    .replace(' role="img" aria-label=""', ' aria-hidden="true"');
  return {
    fijas,
    viva: capaViva.replace("<svg ", `<svg data-datos="${huella}" data-vivo="${esc(JSON.stringify(vivo))}" `),
  };
}

// Sombra de contacto horneada: la huella de la pieza en el piso y dos escalones translúcidos que
// se abren, sin desenfoque (el filtro blur repinta caro). pad = cuánto se abre.
export function sombra(plan, z, P, { pad = 4, pasos = 3 } = {}) {
  const out = [];
  for (let j = pasos; j >= 1; j--) {
    const g = (pad * j) / pasos;
    const pl = { x: plan.x - g, y: plan.y - g, w: plan.w + 2 * g, d: plan.d + 2 * g, r: (plan.r ?? 0) + g };
    out.push(`<path class="sombra" d="${k.planOutline(pl, z, P, 6)}"/>`);
  }
  return out.join("");
}
// La misma sombra bajo una pieza redonda.
export function sombraRedonda(cx, cy, r, z, P, { pad = 3, pasos = 3 } = {}) {
  const out = [];
  for (let j = pasos; j >= 1; j--) out.push(`<path class="sombra" d="${k.ring(cx, cy, r + (pad * j) / pasos, z, P, 40)}"/>`);
  return out.join("");
}

// Matriz de pantalla de un plano: lo que se dibuja en (u, v) locales cae en el plano del mundo.
// plano "z": horizontal a la altura z (u = x, v = y); "x": vertical en x = c (u = y, v = z);
// "y": vertical en y = c (u = x, v = z). Devuelve [a, b, c, d, e, f] para matrix().
export function matrizPlano(P, plano, c = 0) {
  const o = plano === "z" ? [0, 0, c] : plano === "x" ? [c, 0, 0] : [0, c, 0];
  const u = plano === "y" ? [1, 0, 0] : plano === "x" ? [0, 1, 0] : [1, 0, 0];
  const v = plano === "z" ? [0, 1, 0] : [0, 0, 1];
  const O = k.iso(o, P);
  const U = k.iso(o.map((q, i) => q + u[i]), P), V = k.iso(o.map((q, i) => q + v[i]), P);
  const r3 = (x) => Math.round(x * 1000) / 1000;
  return [U[0] - O[0], U[1] - O[1], V[0] - O[0], V[1] - O[1], O[0], O[1]].map(r3);
}

export const porProf = (pts, P) =>
  [...pts].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));

// Un rectángulo en el plano de una cara +y (frente), de x0 a x1 y de z0 a z1, a la profundidad y.
export const enFrente = (x0, x1, z0, z1, y, P) =>
  k.pathOf([[x0, y, z0], [x1, y, z0], [x1, y, z1], [x0, y, z1]].map((p) => k.iso(p, P)), true);
// Lo mismo en una cara +x (costado derecho), de y0 a y1.
export const enCostado = (y0, y1, z0, z1, x, P) =>
  k.pathOf([[x, y0, z0], [x, y1, z0], [x, y1, z1], [x, y0, z1]].map((p) => k.iso(p, P)), true);

// Base de banco: sombra horneada, patas con brida, losa biselada, ranura, tornillos en las esquinas.
export function base(PLACA, z, grueso, P, { patas = 12, alto = 6 } = {}) {
  const out = [];
  const piso = z - grueso - alto;
  out.push(sombra(PLACA, piso, P, { pad: 7 }));
  for (const [x, y] of porProf(k.corners(PLACA, patas), P)) {
    out.push(S(k.cylinder(x, y, 5.2, piso, 1.4, P, 24), { tone: "lo" }));
    out.push(S(k.cylinder(x, y, 3.8, piso + 1.4, alto - 1.4, P, 24), { tone: "mid" }));
  }
  out.push(S(k.slabOf(PLACA, z - grueso, grueso, P, 6, 1.2), { tone: "lo" }));
  out.push(L(k.planOutline(k.insetPlan(PLACA, 4), z, P, 4), { tone: "faint" }));
  const torn = k.corners(PLACA, 7.5);
  out.push(L(torn.map(([x, y]) => k.ring(x, y, 1.7, z, P, 14)).join(""), { tone: "lo" }));
  out.push(D(torn.map(([x, y]) => k.iso([x, y, z], P)), { size: 0.45 }));
  return out.join("");
}

// Regla en el borde delantero (+y) de una placa: tira de metal, marcas cada 4 y mayores cada 5.
export function regla(x0, x1, yBorde, z, P) {
  const tira = { x: x0, y: yBorde - 3, w: x1 - x0, d: 2.6, r: 0.6 };
  const out = [S(k.slabOf(tira, z, 0.5, P, 2), { tone: "lo", crease: "none", m: "metal" })];
  const m = k.topTicks(x0 + 2, x1 - 2, 4, 5, yBorde - 0.4, z + 0.5, [-1, -1.8], P);
  out.push(L(m.minor, { tone: "lo" }), L(m.major, { tone: "mid" }));
  return out.join("");
}

// Placa de rótulo plana sobre una cara superior: tres renglones de texto impreso y dos tornillos.
export function placaRotulo(plan, z, P, renglones = [0.8, 0.55, 0.68]) {
  const out = [S(k.slabOf(plan, z, 0.6, P, 3), { tone: "lo" })];
  out.push(L(k.planOutline(k.insetPlan(plan, 1.2), z + 0.6, P, 2), { tone: "faint" }));
  const paso = (plan.d - 4) / (renglones.length + 1);
  out.push(
    L(
      renglones
        .map((f, j) => k.lineOnTop([plan.x + 3.2, plan.y + 2 + paso * (j + 1)], [plan.x + 3.2 + (plan.w - 8) * f, plan.y + 2 + paso * (j + 1)], z + 0.6, P))
        .join(""),
      { tone: "lo", free: true },
    ),
  );
  out.push(D([k.iso([plan.x + plan.w - 2, plan.y + 2, z + 0.6], P), k.iso([plan.x + plan.w - 2, plan.y + plan.d - 2, z + 0.6], P)], { size: 0.4 }));
  return out.join("");
}

// Envolvente convexa (para prismas que giran).
export function casco(pts) {
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

// Una lámpara piloto en una cara vertical (eje "y": cara que mira a +y; "x": a +x). En la capa fija,
// el aro de metal en el plano de la cara y la lente apagada (un domo: en pantalla, un círculo);
// en la viva, la lente encendida con su brillo, que aparece con la escala. r en unidades del mundo:
// con la escala común, r ≥ 1,9 da un piloto de 8 px o más a 1x en las figuras de la portada.
export function lampara(c, r, eje, P) {
  const [cx, cy] = k.iso(c, P);
  const rp = r1(r * P.scale);
  const aro = `<path class="lamp-aro" d="${k.sideRing(c, r + 0.8, eje, P, 28)}"/>`;
  const lente = `<circle class="lamp-lente" cx="${r1(cx)}" cy="${r1(cy)}" r="${rp}"/>`;
  const brillo = (x, y) => `<circle class="lamp-brillo" cx="${r1(x - rp * 0.32)}" cy="${r1(y - rp * 0.36)}" r="${r1(rp * 0.28)}"/>`;
  return {
    fija: aro + lente,
    // la lente encendida: clase de estado (marca-vivo, marca-ambar, marca-revisar) y su pieza viva
    luz: (clase, v, { visible = false } = {}) =>
      `<g${v ? ` data-v="${v}"` : ""} class="${clase}" data-c="${r1(cx)} ${r1(cy)}"${visible ? "" : ' style="transform:scale(0);opacity:0"'}>` +
      `<circle class="luz" cx="${r1(cx)}" cy="${r1(cy)}" r="${rp}"/>${brillo(cx, cy)}</g>`,
    centro: [r1(cx), r1(cy)],
  };
}
