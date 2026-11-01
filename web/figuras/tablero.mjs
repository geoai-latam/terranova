// Fig. tablero: una mesa de instrumentos. Delante, un reloj por indicador (población, pobreza,
// educación, salud: los del catálogo), con la franja de los municipios comparables y la aguja de
// tu municipio; detrás, un trazador de pórtico que dibuja en papel la tendencia del indicador
// elegido. Lo que se mueve: la aguja del reloj elegido se enciende y el trazador dibuja su serie.
// Las cifras son ilustrativas; los indicadores y sus entidades, reales.
import { D, L, S, base, encuadre, k, regla, svgDe } from "./comun.mjs";

export function tablero(DATOS, huella) {
  const { indicadores } = DATOS.tablero;
  const n = indicadores.length;
  const PLACA = { x: -14, y: -50, w: 170, d: 98, r: 4 };
  const BED = { x: 0, y: -44, w: 140, d: 46, r: 2 }; // cama del trazador
  const PAPEL = { x: 10, y: -38, w: 120, d: 34, r: 0.4 };
  const ZB = 6, ZP = ZB + 0.3; // cara de la cama y del papel
  const R = 13, ZD = 9; // reloj: radio y alto
  const DIAL = (i) => [24 + i * 34, 26];
  const DESDE = -0.75 * Math.PI, ARCO = 1.5 * Math.PI;
  const { P, ancho, alto } = encuadre([...k.boxCorners(PLACA, -14, 0), [BED.x, BED.y, 26], [BED.x + BED.w, BED.y, 26]], { azimuth: 57 });
  const at = (p) => k.iso(p, P);
  const out = [];

  out.push(base(PLACA, 0, 5, P));
  out.push(regla(PLACA.x + 12, PLACA.x + PLACA.w - 12, PLACA.y + PLACA.d, 0, P));

  // el trazador: cama con su ranura, papel con cuadrícula y las cuatro series (una visible)
  out.push(S(k.slabOf(BED, 0, ZB, P, 3, 0.6), { tone: "mid", inner: L(k.sideSeam(BED, 2, P, 3), { tone: "faint" }) }));
  out.push(S(k.slabOf(PAPEL, ZB, 0.3, P, 1), { tone: "hi", crease: "none" }));
  const reticula = [];
  for (let y = PAPEL.y + 4.25; y < PAPEL.y + PAPEL.d; y += 4.25) reticula.push(k.lineOnTop([PAPEL.x, y], [PAPEL.x + PAPEL.w, y], ZP, P));
  for (let x = PAPEL.x + 10; x < PAPEL.x + PAPEL.w; x += 10) reticula.push(k.lineOnTop([x, PAPEL.y], [x, PAPEL.y + PAPEL.d], ZP, P));
  out.push(L(reticula.join(""), { tone: "faint" }));
  // pinzas del papel en las esquinas
  for (const [x, y] of k.corners(PAPEL, 0)) out.push(S(k.slabOf({ x: x - 2.5, y: y - 2.5, w: 5, d: 5, r: 1 }, ZP, 1.2, P, 2), { tone: "mid" }));
  // las series: x del tiempo y del valor (0 abajo del papel, 1 arriba)
  const puntoSerie = (v, j, m) => [PAPEL.x + 8 + (j / (m - 1)) * (PAPEL.w - 16), PAPEL.y + PAPEL.d - 5 - v * (PAPEL.d - 10)];
  const series = indicadores.map((ind) => ind.serie.map((v, j) => puntoSerie(v, j, ind.serie.length)));
  series.forEach((pts, i) => {
    const d = k.pathOf(pts.map(([x, y]) => at([x, y, ZP])));
    out.push(`<path class="serie" data-serie="${i}" pathLength="100" d="${d}"/>`);
  });
  // rieles del pórtico a lo largo de la cama, con topes
  for (const y of [BED.y + 1, BED.y + BED.d - 4]) {
    out.push(S(k.slabOf({ x: BED.x + 2, y, w: BED.w - 4, d: 3, r: 0.6 }, ZB, 2, P, 2), { tone: "lo" }));
    for (const x of [BED.x + 3, BED.x + BED.w - 6]) out.push(S(k.slabOf({ x, y: y - 0.5, w: 3, d: 4, r: 0.6 }, ZB + 2, 2, P, 2), { tone: "mid" }));
  }

  // el pórtico (se mueve en x) con el carro y la pluma (se mueven en y), armado en x = X0, y = Y0
  const X0 = PAPEL.x + 8, Y0 = PAPEL.y + PAPEL.d - 5;
  const g = [];
  const bloque = (y) => S(k.slabOf({ x: X0 - 4, y, w: 8, d: 6, r: 1 }, ZB + 2, 10, P, 2, 0.4), { tone: "mid", inner: L(k.sideSeam({ x: X0 - 4, y, w: 8, d: 6, r: 1 }, ZB + 5, P, 2), { tone: "faint" }) });
  g.push(bloque(BED.y - 1));
  const puente = { x: X0 - 3, y: BED.y - 1, w: 6, d: BED.d + 2, r: 0.8 };
  g.push(S(k.slabOf(puente, ZB + 12, 4, P, 2, 0.4), { tone: "hi", inner: L(k.sideSeam(puente, ZB + 14, P, 2), { tone: "faint" }) }));
  g.push(D([at([X0, BED.y + 2, ZB + 16]), at([X0, BED.y + BED.d - 2, ZB + 16])], { size: 0.42 }));
  const carro = [];
  carro.push(S(k.slabOf({ x: X0 - 5, y: Y0 - 4, w: 10, d: 8, r: 1.2 }, ZB + 9, 9, P, 3, 0.5), { tone: "hi" }));
  carro.push(S(k.cylinder(X0, Y0, 1.6, ZP + 0.4, 8.6, P, 16), { tone: "mid", crease: "none" }));
  carro.push(S(k.cylinder(X0, Y0, 2.6, ZB + 18, 2.4, P, 20), { tone: "mid" }));
  carro.push(L(k.knurl(X0, Y0, 2.6, ZB + 18, ZB + 20.4, 18, P), { tone: "lo" }));
  g.push(`<g data-carro>${carro.join("")}</g>`);
  g.push(bloque(BED.y + BED.d - 5));
  out.push(`<g data-portico>${g.join("")}</g>`);

  // los relojes, de atrás hacia adelante (todos en la misma fila: de izquierda a derecha)
  const centros = [];
  indicadores.forEach((ind, i) => {
    const [cx, cy] = DIAL(i);
    const r = [];
    r.push(`<path class="iso-halo" d="${k.haloOf({ x: cx - R, y: cy - R, w: 2 * R, d: 2 * R, r: R }, 0, 2, P)}"/>`);
    // corona en el costado de atrás (detrás de la caja, se dibuja antes)
    r.push(S(k.slabOf({ x: cx - 1.8, y: cy - R - 2.4, w: 3.6, d: 3, r: 0.6 }, ZD - 6, 3.4, P, 2), { tone: "mid" }));
    r.push(S(k.cylinder(cx, cy, R + 2, 0, 2, P, 48), { tone: "lo" }));
    r.push(S(k.cylinder(cx, cy, R, 2, ZD - 2, P, 56, 0.8), { tone: "hi", crease: "lo" }));
    r.push(L(k.knurl(cx, cy, R, ZD - 3, ZD, 64, P, 0.3), { tone: "lo" }));
    r.push(L(k.sideArc(cx, cy, R, ZD - 3, P, 40), { tone: "faint" }));
    r.push(L(k.ring(cx, cy, R - 1.6, ZD, P, 56), { tone: "lo" }));
    // franja de los comparables: dos arcos y sus extremos, sobre la esfera
    const [a, b] = ind.comparables;
    const arco = (rr, f0, f1) => {
      const pts = [];
      for (let q = 0; q <= 16; q++) {
        const t = DESDE + ARCO * (f0 + (f1 - f0) * (q / 16));
        pts.push([cx + Math.sin(t) * rr, cy - Math.cos(t) * rr]);
      }
      return pts;
    };
    const franja = [...arco(R - 1.6, a, b), ...arco(R - 4.4, a, b).reverse()];
    r.push(`<path class="franja" d="${k.pathOf(franja.map(([x, y]) => at([x, y, ZD])), true)}"/>`);
    const t = k.radialTicks(cx, cy, R - 1.6, 30, 5, ZD, [1, 2.2], P, DESDE, ARCO);
    r.push(L(t.minor, { tone: "lo" }), L(t.major, { tone: "mid" }));
    r.push(`<path class="aguja" data-aguja="${i}" d=""/>`);
    r.push(L(k.ring(cx, cy, 1.4, ZD, P, 14), { tone: "hi" }));
    out.push(`<g data-reloj="${i}">${r.join("")}</g>`);
    centros.push([cx, cy]);
  });
  // tornillos de la mesa entre relojes
  out.push(D(indicadores.slice(1).map((_, i) => at([DIAL(i)[0] + 17, DIAL(i)[1] + 10, 0])), { size: 0.42 }));

  const r1 = (v) => Math.round(v * 10) / 10;
  return svgDe({
    huella,
    ancho,
    alto,
    clase: "fig-tablero",
    etiqueta: `Una mesa de instrumentos: ${n} relojes, uno por indicador (${indicadores.map((x) => `${x.t.toLowerCase()}, ${x.e}`).join("; ")}), con la franja de los municipios comparables y la aguja de tu municipio, y detrás un trazador que dibuja la tendencia del indicador elegido. Las cifras son ilustrativas.`,
    cuerpo: out,
    vivo: {
      P,
      centros,
      R: R - 3.2,
      zd: ZD,
      desde: DESDE,
      arco: ARCO,
      valores: indicadores.map((x) => x.valor),
      series: series.map((pts) => pts.map(([x, y]) => [r1(x - X0), r1(y - Y0)])),
      ex: k.axisVector(P, [1, 0, 0]).map((v) => Math.round(v * 1000) / 1000),
      ey: k.axisVector(P, [0, 1, 0]).map((v) => Math.round(v * 1000) / 1000),
      lecturas: indicadores.map((x) => `${x.t.toLowerCase()} · ${x.e} · tu municipio frente a sus comparables`),
    },
  });
}
