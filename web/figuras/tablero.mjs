// Fig. tablero: una mesa de instrumentos. Delante, un reloj por indicador (los del catálogo, todos
// con serie publicada por su entidad), con la franja de los municipios comparables y la aguja de tu
// municipio; detrás, un trazador de pórtico que dibuja en papel la serie del indicador elegido. Lo que
// se mueve: el pórtico vuelve al principio, la aguja del reloj elegido (la única ámbar) barre hasta su
// lectura y oscila solo al asentarse, y la pluma dibuja la serie. Las cifras son ilustrativas; los
// indicadores, sus entidades y que cada uno tenga serie, reales.
import { D, L, S, base, encuadre, k, matrizPlano, r1, regla, sombraRedonda, svgDe } from "./comun.mjs";

export function tablero(DATOS, huella) {
  const { indicadores } = DATOS.tablero;
  const n = indicadores.length;
  const PLACA = { x: -14, y: -50, w: 170, d: 98, r: 4 };
  const BED = { x: 0, y: -44, w: 140, d: 46, r: 2 }; // cama del trazador
  const PAPEL = { x: 10, y: -38, w: 120, d: 34, r: 0.4 };
  const ZB = 6, ZP = ZB + 0.3; // cara de la cama y del papel
  const R = 13, ZD = 9, ZF = ZD + 0.3; // reloj: radio, alto de la caja y de la esfera
  const DIAL = (i) => [24 + i * 34, 26];
  const DESDE = -0.75 * Math.PI, ARCO = 1.5 * Math.PI;
  const { P, ancho, alto } = encuadre([...k.boxCorners(PLACA, -14, 0), [BED.x, BED.y, 26], [BED.x + BED.w, BED.y, 26]], { azimuth: 57 });
  const at = (p) => k.iso(p, P);
  const fija = [];
  const viva = [];

  fija.push(base(PLACA, 0, 5, P));
  fija.push(regla(PLACA.x + 12, PLACA.x + PLACA.w - 12, PLACA.y + PLACA.d, 0, P));

  // el trazador: cama con su ranura, papel con cuadrícula y pinzas, rieles con topes
  fija.push(S(k.slabOf(BED, 0, ZB, P, 3, 0.6), { m: "metal", tone: "mid", inner: L(k.sideSeam(BED, 2, P, 3), { tone: "faint" }) }));
  fija.push(S(k.slabOf(PAPEL, ZB, 0.3, P, 1), { m: "papel", tone: "hi", crease: "none" }));
  const reticula = [];
  for (let y = PAPEL.y + 4.25; y < PAPEL.y + PAPEL.d - 0.1; y += 4.25) reticula.push(k.lineOnTop([PAPEL.x, y], [PAPEL.x + PAPEL.w, y], ZP, P));
  for (let x = PAPEL.x + 10; x < PAPEL.x + PAPEL.w; x += 10) reticula.push(k.lineOnTop([x, PAPEL.y], [x, PAPEL.y + PAPEL.d], ZP, P));
  fija.push(L(reticula.join(""), { tone: "faint" }));
  // un punto de la serie en el papel: x por su lugar en el tiempo, y por su valor (0 abajo, 1 arriba)
  const puntoSerie = (v, j, m) => [PAPEL.x + 8 + (j / (m - 1)) * (PAPEL.w - 16), PAPEL.y + PAPEL.d - 5 - v * (PAPEL.d - 10)];
  for (const [x, y] of k.corners(PAPEL, 0)) fija.push(S(k.slabOf({ x: x - 2.5, y: y - 2.5, w: 5, d: 5, r: 1 }, ZP, 1.2, P, 2), { m: "acero", tone: "mid" }));
  for (const y of [BED.y + 1, BED.y + BED.d - 4]) {
    fija.push(S(k.slabOf({ x: BED.x + 2, y, w: BED.w - 4, d: 3, r: 0.6 }, ZB, 2, P, 2), { m: "acero", tone: "lo" }));
    for (const x of [BED.x + 3, BED.x + BED.w - 6]) fija.push(S(k.slabOf({ x, y: y - 0.5, w: 3, d: 4, r: 0.6 }, ZB + 2, 2, P, 2), { m: "metal", tone: "mid" }));
  }

  // las series, en tramos cortos que aparecen cuando la pluma pasa (capa viva)
  const TRAMOS = 28;
  const X0 = PAPEL.x + 8, Y0 = PAPEL.y + PAPEL.d - 5, LARGO = PAPEL.w - 16;
  const yDe = (serie, f) => {
    const u = f * (serie.length - 1), j = Math.min(serie.length - 2, Math.floor(u)), q = u - j;
    return puntoSerie(serie[j] + (serie[j + 1] - serie[j]) * q, 0, 2)[1];
  };
  indicadores.forEach((ind, i) => {
    const tramos = [];
    for (let j = 0; j < TRAMOS; j++) {
      const a = j / TRAMOS, b = (j + 1) / TRAMOS;
      const d = k.pathOf([[X0 + a * LARGO, yDe(ind.serie, a)], [X0 + ((a + b) / 2) * LARGO, yDe(ind.serie, (a + b) / 2)], [X0 + b * LARGO, yDe(ind.serie, b)]].map(([x, y]) => at([x, y, ZP])));
      tramos.push(`<path class="serie" data-v="s${i}_${j}" style="opacity:0" d="${d}"/>`);
    }
    viva.push(`<g>${tramos.join("")}</g>`);
  });

  // el pórtico (se mueve en x) con el carro y la pluma (se mueven en y), armado en X0, Y0
  const g = [];
  const bloque = (y) => S(k.slabOf({ x: X0 - 4, y, w: 8, d: 6, r: 1 }, ZB + 2, 10, P, 2, 0.4), { m: "metal", tone: "mid", inner: L(k.sideSeam({ x: X0 - 4, y, w: 8, d: 6, r: 1 }, ZB + 5, P, 2), { tone: "faint" }) });
  g.push(bloque(BED.y - 1));
  const puente = { x: X0 - 3, y: BED.y - 1, w: 6, d: BED.d + 2, r: 0.8 };
  g.push(S(k.slabOf(puente, ZB + 12, 4, P, 2, 0.4), { m: "papel", tone: "hi", inner: L(k.sideSeam(puente, ZB + 14, P, 2), { tone: "faint" }) }));
  g.push(D([at([X0, BED.y + 2, ZB + 16]), at([X0, BED.y + BED.d - 2, ZB + 16])], { size: 0.42 }));
  const carro = [];
  carro.push(S(k.cylinder(X0, Y0, 0.9, ZP, 9.4, P, 12), { m: "acero", tone: "mid", crease: "none" }));
  carro.push(S(k.slabOf({ x: X0 - 5, y: Y0 - 4, w: 10, d: 8, r: 1.2 }, ZB + 9, 9, P, 3, 0.5), { m: "metal", tone: "mid", inner: L(k.sideSeam({ x: X0 - 5, y: Y0 - 4, w: 10, d: 8, r: 1.2 }, ZB + 12, P, 3), { tone: "faint" }) }));
  carro.push(S(k.cylinder(X0, Y0, 2.6, ZB + 18, 2.4, P, 20), { m: "acero", tone: "mid" }));
  carro.push(L(k.knurl(X0, Y0, 2.6, ZB + 18, ZB + 20.4, 18, P), { tone: "lo" }));
  g.push(`<g data-v="carro">${carro.join("")}</g>`);
  g.push(bloque(BED.y + BED.d - 5));
  viva.push(`<g data-v="portico">${g.join("")}</g>`);

  // los relojes (capa viva: tapan el pórtico y llevan las agujas), de izquierda a derecha
  const centros = [];
  const MZ = matrizPlano(P, "z", ZF + 0.25);
  indicadores.forEach((ind, i) => {
    const [cx, cy] = DIAL(i);
    const r = [];
    r.push(sombraRedonda(cx, cy, R + 2, 0, P));
    // corona en el costado de atrás (detrás de la caja, se dibuja antes)
    r.push(S(k.slabOf({ x: cx - 1.8, y: cy - R - 2.4, w: 3.6, d: 3, r: 0.6 }, ZD - 6, 3.4, P, 2), { m: "metal", tone: "mid" }));
    r.push(S(k.cylinder(cx, cy, R + 2, 0, 2, P, 48), { m: "acero", tone: "lo" }));
    r.push(S(k.cylinder(cx, cy, R, 2, ZD - 2, P, 56, 0.8), { m: "agua-honda", tone: "hi", crease: "lo" }));
    r.push(L(k.knurl(cx, cy, R, ZD - 3, ZD, 64, P, 0.3), { tone: "mid" }));
    r.push(L(k.sideArc(cx, cy, R, ZD - 3, P, 40), { tone: "faint" }));
    // la esfera: un disco de papel con su aro, la franja de los comparables y las marcas
    r.push(S(k.cylinder(cx, cy, R - 1.6, ZD, 0.3, P, 56), { m: "papel", tone: "lo", crease: "none" }));
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
    r.push(`<path class="franja" d="${k.pathOf(franja.map(([x, y]) => at([x, y, ZF])), true)}"/>`);
    const t = k.radialTicks(cx, cy, R - 1.6, 30, 5, ZF, [1, 2.2], P, DESDE, ARCO);
    r.push(L(t.minor, { tone: "lo" }), L(t.major, { tone: "mid" }));
    // las agujas: tinta y su copia ámbar (la del reloj elegido); se dibujan en el plano de la esfera
    // apuntando a 0 y giran sobre el centro
    const aguja = `M${r1(cx - 0.55)} ${r1(cy + 2.4)}L${r1(cx + 0.55)} ${r1(cy + 2.4)}L${r1(cx + 0.14)} ${r1(cy - (R - 3.2))}L${r1(cx - 0.14)} ${r1(cy - (R - 3.2))}Z`;
    // la del reloj elegido, en ámbar, es una pala con su cubo: se lee a 1x (~10 px o más)
    const pala = `M${r1(cx - 1.3)} ${r1(cy + 3)}L${r1(cx + 1.3)} ${r1(cy + 3)}L${r1(cx + 0.3)} ${r1(cy - (R - 3))}L${r1(cx - 0.3)} ${r1(cy - (R - 3))}Z`;
    const cubo = `<circle class="aguja-ambar" cx="${cx}" cy="${cy}" r="2.6"/>`;
    r.push(
      `<g transform="matrix(${MZ.join(" ")})"><g data-v="aguja${i}" data-centro="${cx} ${cy}"><path class="aguja" d="${aguja}"/></g>` +
        `<g data-v="ambar${i}" data-centro="${cx} ${cy}" style="opacity:0"><path class="aguja-ambar" d="${pala}"/>${cubo}</g></g>`,
    );
    r.push(L(k.ring(cx, cy, 1.4, ZF + 0.3, P, 14), { tone: "hi" }));
    r.push(D([at([cx, cy, ZF + 0.3])], { size: 0.6, tone: "hi" }));
    viva.push(`<g data-reloj="${i}">${r.join("")}</g>`);
    centros.push(at([cx, cy, ZF]).map((v) => Math.round(v)));
  });
  // tornillos de la mesa entre relojes
  viva.push(D(indicadores.slice(1).map((_, i) => at([DIAL(i)[0] + 17, DIAL(i)[1] + 10, 0])), { size: 0.42 }));

  const r3 = (v) => Math.round(v * 1000) / 1000;
  return svgDe({
    huella,
    ancho,
    alto,
    clase: "fig-tablero",
    etiqueta: `Una mesa de instrumentos: ${n} relojes, uno por indicador (${indicadores.map((x) => `${x.t.toLowerCase()}, ${x.e}`).join("; ")}), con la franja de los municipios comparables y la aguja de tu municipio, y detrás un trazador que dibuja la serie del indicador elegido. Las cifras son ilustrativas.`,
    fija,
    viva,
    vivo: {
      centros,
      desde: (DESDE * 180) / Math.PI,
      arco: (ARCO * 180) / Math.PI,
      valores: indicadores.map((x) => x.valor),
      tramos: TRAMOS,
      largo: LARGO,
      series: indicadores.map((ind) => Array.from({ length: 41 }, (_, q) => r1(yDe(ind.serie, q / 40) - Y0))),
      ex: k.axisVector(P, [1, 0, 0]).map(r3),
      ey: k.axisVector(P, [0, 1, 0]).map(r3),
      ind: indicadores.map((x) => ({ t: x.t.toLowerCase(), e: x.e, m: x.m })),
    },
  });
}
